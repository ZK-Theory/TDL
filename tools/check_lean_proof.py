#!/usr/bin/env python3
# Research context: docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md
# Purpose: Acceptor-side verification harness for the `lean_proof` evidence class,
#   scoped to the S2 pilot bundle. Implements the Key-A machine checks of 05a §3
#   items 0-8: the acceptor ACCEPTS a promoted bundle by RE-EXECUTING it (C1) -
#   a clean `lake build`, a sorry/admit scan, `#print axioms` per theorem with the
#   axiom set constrained to {propext, Classical.choice, Quot.sound}, native_decide/
#   FFI rejection, a declaration-kind scan (only theorem/lemma/example + proof
#   bodies), and the equality-obligation check (item 5). Producer build.log /
#   axiom-audit.md are advisory only and never consulted for a verdict.
#
#   Scope boundary (05a §1/§5, task brief): this is the standalone enforcement tool
#   for the S2 pilot's Key-A machine checks ONLY. It does NOT implement the ARS W5
#   runtime, the W6 fixture materialization, any pack machinery, or the Key-B human
#   obligations - referent adequacy (§3 item 9), the full elaborated-type diff
#   (§3 item 8 Key B(b)), the mutation obligation (§3 item 7), or scratch-layout
#   review (§3 item 10) - which stay behind their own gates. It verifies bytes; it
#   never judges whether the authored statement is what the claim needs.
"""Standalone lean_proof acceptance harness (05a §3 items 0-8, Key A machine checks).

Exit codes:
    0 - ADMISSIBLE: every Key-A machine check passed under acceptor re-execution.
    1 - INADMISSIBLE: at least one acceptance item failed (the failed item(s) named);
        a constant-equality mismatch additionally emits a discrepancy record.
    2 - HARNESS/ENVIRONMENT error: the bundle, manifest, or Lean toolchain is
        absent or malformed, so acceptance could not be established. The tool fails
        CLOSED - it never reports admissible on a skipped check.

Usage:
    check_lean_proof.py --bundle <dir> --repo-commit <sha>
                        [--project-dir <dir>] [--json-out <path>]
                        [--emit-discrepancies <path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # noqa: S404 - the whole point of C1 is to shell out and re-execute
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

EXIT_ADMISSIBLE = 0
EXIT_INADMISSIBLE = 1
EXIT_ENV_ERROR = 2

#: 05a §3 item 3 - the only axioms a promoted theorem may transitively depend on.
ALLOWED_AXIOMS: frozenset[str] = frozenset({"propext", "Classical.choice", "Quot.sound"})

#: 05a §3 item 8 - promoted files may carry only these (proof-carrying) kinds.
#: `lemma` is Lean's theorem synonym and is the vehicle for the §4 "auxiliary
#: private lemmas" the prover is allowed to supply.
ALLOWED_DECL_KINDS: frozenset[str] = frozenset({"theorem", "lemma", "example"})

#: Any of these in a promoted file is prover-authored drift (05a §3 item 8): it can
#: silently change the meaning of a promoted signature (def/abbrev/notation/macro/
#: instance/...) or smuggle in a new axiom.
DISALLOWED_DECL_KINDS: frozenset[str] = frozenset(
    {
        "def",
        "abbrev",
        "notation",
        "macro",
        "macro_rules",
        "syntax",
        "elab",
        "instance",
        "structure",
        "inductive",
        "class",
        "axiom",
        "opaque",
        "deriving",
        "infix",
        "infixl",
        "infixr",
        "prefix",
        "postfix",
        "declare_syntax_cat",
    }
)

_DECL_KEYWORDS: frozenset[str] = ALLOWED_DECL_KINDS | DISALLOWED_DECL_KINDS
_MODIFIERS: frozenset[str] = frozenset(
    {"private", "protected", "noncomputable", "partial", "unsafe", "scoped", "local", "mutual", "nonrec"}
)

_ATTR_RE = re.compile(r"@\[[^\]]*\]")
_HOLE_RE = re.compile(r"(?<![\w.])(sorry|admit)(?![\w'])")
_NATIVE_RE = re.compile(r"\bnative_decide\b|@\[\s*extern|@\[\s*implemented_by|\bimplemented_by\b|\bextern\b")
_REL_OPS = ("=", "≤", "≥", "<", ">", "≠")

#: Tactics that discharge a goal with a proof term the kernel re-checks. decide,
#: norm_num, rfl, simp, and omega all qualify; native_decide (Lean.ofReduceBool /
#: trustCompiler) and sorry/admit do not. `Nat.ble` is @[extern], so `decide`
#: stalls on the S2 greedy/pair-count constants and they are pinned by `norm_num`
#: — still kernel-checked, and must be allowed to anchor a constant (obs 86, 87).
_KERNEL_TACTIC_RE = re.compile(r"\b(?:decide|norm_num|rfl|simp|omega)\b")


# --------------------------------------------------------------------------- #
# Errors (both map to EXIT_ENV_ERROR - fail closed)                           #
# --------------------------------------------------------------------------- #


class BundleError(Exception):
    """The bundle or its manifest is absent, malformed, or internally unresolvable."""


class ToolchainError(Exception):
    """The Lean toolchain could not be found or failed to run - acceptance cannot be established."""


# --------------------------------------------------------------------------- #
# Result records                                                               #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single acceptance item."""

    item: str
    passed: bool
    detail: str


@dataclass
class AcceptanceOutcome:
    """Aggregate verdict over all Key-A machine checks."""

    admissible: bool
    results: list[CheckResult]
    discrepancies: list[dict[str, object]] = field(default_factory=list)

    @property
    def failed_items(self) -> list[str]:
        """Item labels of every check that failed, in evaluation order."""
        return [r.item for r in self.results if not r.passed]

    @property
    def first_failure(self) -> str | None:
        """The first failed item label, or ``None`` when admissible."""
        failed = self.failed_items
        return failed[0] if failed else None


# --------------------------------------------------------------------------- #
# Toolchain abstraction - the real one shells out; tests inject a fake         #
# --------------------------------------------------------------------------- #


class LeanToolchain(Protocol):
    """The acceptor's own clean re-execution surface (05a §3 item 0 / C1)."""

    def available(self) -> bool:
        """True when the toolchain can actually be invoked (fail closed otherwise)."""
        ...

    def lake_build(self, project_dir: Path, targets: list[str] | None = None) -> tuple[int, str]:
        """Run ``lake build`` (optionally for named ``targets``) in ``project_dir``; return (exit_code, output)."""
        ...

    def print_axioms(self, project_dir: Path, imports: list[str], theorems: list[str]) -> dict[str, str]:
        """Return the raw ``#print axioms`` line for each theorem, keyed by theorem name."""
        ...


class RealLeanToolchain:
    """Shells out to ``lake``/``lean`` (via elan) to re-execute the bundle for real.

    Untested in CI (no Lean toolchain on the build box); the verified logic lives in
    the pure checks + orchestration exercised with an injected fake. ``available``
    gates every call so a missing toolchain fails closed (EXIT_ENV_ERROR).
    """

    def __init__(self, timeout_s: int = 1800) -> None:
        self.timeout_s = timeout_s

    def available(self) -> bool:
        return shutil.which("lake") is not None

    def lake_build(self, project_dir: Path, targets: list[str] | None = None) -> tuple[int, str]:
        try:
            proc = subprocess.run(  # noqa: S603, S607 - fixed argv, trusted binary on PATH
                ["lake", "build", *(targets or [])],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - real-toolchain only
            raise ToolchainError(f"lake build could not be executed: {exc}") from exc
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def print_axioms(
        self, project_dir: Path, imports: list[str], theorems: list[str]
    ) -> dict[str, str]:  # pragma: no cover - real-toolchain only
        lines = [f"import {mod}" for mod in imports]
        lines += [f"#print axioms {thm}" for thm in theorems]
        query = "\n".join(lines) + "\n"
        with tempfile.TemporaryDirectory(dir=str(project_dir)) as tmp:
            query_file = Path(tmp) / "_axiom_query.lean"
            query_file.write_text(query, encoding="utf-8")
            try:
                proc = subprocess.run(  # noqa: S603, S607 - fixed argv, trusted binary on PATH
                    ["lake", "env", "lean", str(query_file)],
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_s,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ToolchainError(f"#print axioms could not be executed: {exc}") from exc
        return _split_axiom_output(proc.stdout or "", theorems)


def _split_axiom_output(stdout: str, theorems: list[str]) -> dict[str, str]:  # pragma: no cover - real-toolchain only
    """Group raw ``lean`` stdout into one axiom line per theorem (best effort)."""
    out: dict[str, str] = {}
    for thm in theorems:
        match = re.search(rf"'{re.escape(thm)}'[^\n]*", stdout)
        if match:
            out[thm] = match.group(0)
    return out


# --------------------------------------------------------------------------- #
# Lean source scanning helpers (pure - the tested core)                        #
# --------------------------------------------------------------------------- #


def strip_comments(text: str) -> str:
    """Remove Lean block ``/- -/`` and line ``--`` comments (non-nested; adequate for promoted files)."""
    text = re.sub(r"/-.*?-/", " ", text, flags=re.DOTALL)
    text = re.sub(r"--[^\n]*", "", text)
    return text


def _decl_head(line: str) -> tuple[str, str] | None:
    """Return (kind, name) when ``line`` begins a declaration, else ``None``."""
    stripped = _ATTR_RE.sub("", line).strip()
    if not stripped:
        return None
    tokens = stripped.split()
    idx = 0
    while idx < len(tokens) and tokens[idx] in _MODIFIERS:
        idx += 1
    if idx >= len(tokens):
        return None
    kind = tokens[idx]
    if kind not in _DECL_KEYWORDS:
        return None
    name = ""
    if idx + 1 < len(tokens):
        name = re.split(r"[\s:({\[]", tokens[idx + 1])[0]
    return kind, name


def iter_declarations(text: str) -> list[tuple[str, str, str]]:
    """Split promoted source into (kind, name, block) declarations.

    A block runs from a declaration head to the next head (or EOF), so the proof
    body travels with its declaration. Comments are stripped first.
    """
    lines = strip_comments(text).splitlines()
    decls: list[tuple[str, str, str]] = []
    cur_head: tuple[str, str] | None = None
    buf: list[str] = []
    for line in lines:
        head = _decl_head(line)
        if head is not None:
            if cur_head is not None:
                decls.append((cur_head[0], cur_head[1], "\n".join(buf)))
            cur_head = head
            buf = [line]
        elif cur_head is not None:
            buf.append(line)
    if cur_head is not None:
        decls.append((cur_head[0], cur_head[1], "\n".join(buf)))
    return decls


# --------------------------------------------------------------------------- #
# Individual acceptance checks                                                 #
# --------------------------------------------------------------------------- #


def verify_file_integrity(bundle_dir: Path, manifest: dict) -> CheckResult:
    """Recompute promoted-file hashes; metadata is suspicion, content is verdict.

    A text file's bytes differ between checkouts under ``core.autocrlf`` (LF vs
    CRLF), so a raw sha256 can false-flag a byte-identical file (obs 71). Accept a
    match against either the raw bytes OR the EOL-normalized (CRLF->LF) bytes: a
    CRLF checkout of an LF-recorded bundle is then not a spurious integrity
    failure, while a genuine content change still fails both.
    """
    bad: list[str] = []
    for entry in manifest["promoted_files"]:
        recorded = entry.get("sha256")
        if not recorded:
            bad.append(f"{entry['path']}: no recorded sha256")
            continue
        data = (bundle_dir / entry["path"]).read_bytes()
        raw = hashlib.sha256(data).hexdigest()
        normalized = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
        if recorded not in (raw, normalized):
            bad.append(f"{entry['path']}: sha256 {raw} != recorded {recorded}")
    if bad:
        return CheckResult("file-integrity", False, "; ".join(bad))
    return CheckResult("file-integrity", True, "promoted file hashes match manifest")


def scan_holes(files: dict[str, str]) -> CheckResult:
    """05a §3 item 2 - reject any ``sorry`` / ``admit`` in promoted files (grep)."""
    hits: list[str] = []
    for path, text in files.items():
        for match in _HOLE_RE.finditer(strip_comments(text)):
            hits.append(f"{path}: {match.group(1)}")
    if hits:
        return CheckResult("no-holes", False, "sorry/admit present: " + "; ".join(hits))
    return CheckResult("no-holes", True, "no sorry/admit in promoted files")


def scan_declaration_kinds(files: dict[str, str]) -> CheckResult:
    """05a §3 item 8 - only theorem/lemma/example allowed; any def/notation/... is drift."""
    offenders: list[str] = []
    for path, text in files.items():
        for kind, name, _ in iter_declarations(text):
            if kind in DISALLOWED_DECL_KINDS:
                offenders.append(f"{path}: {kind} {name}".rstrip())
    if offenders:
        return CheckResult(
            "declaration-kind",
            False,
            "prover-authored non-theorem declaration(s) (drift): " + "; ".join(offenders),
        )
    return CheckResult("declaration-kind", True, "only theorem/lemma/example declarations present")


def _native_hit_approved(hit: str, approved: list) -> bool:
    """True iff some approval entry explicitly matches this specific hit.

    An approval entry is either a bare string or an object with a ``match`` key; its
    value is a substring that must appear in the hit descriptor (``"<file>: <token>"``).
    This is per-occurrence by construction - a single approval never waives an
    unrelated native_decide/FFI use elsewhere in the promoted set (05a §3 item 4).
    """
    for entry in approved:
        matcher = entry.get("match") if isinstance(entry, dict) else entry
        if isinstance(matcher, str) and matcher and matcher in hit:
            return True
    return False


def scan_native_decide(files: dict[str, str], approved: list) -> CheckResult:
    """05a §3 item 4 - reject native_decide / extern / FFI evaluation absent explicit approval.

    Approval is evaluated *per hit*: each detected occurrence must be matched by a
    specific approval entry, or it is rejected. A non-empty approval list is never a
    global waiver.
    """
    hits: list[str] = []
    for path, text in files.items():
        for match in _NATIVE_RE.finditer(strip_comments(text)):
            hits.append(f"{path}: {match.group(0)}")
    if not hits:
        return CheckResult("trusted-computing-base", True, "no native_decide/extern/FFI evaluation")
    approved = approved or []
    unapproved = [hit for hit in hits if not _native_hit_approved(hit, approved)]
    if unapproved:
        return CheckResult(
            "trusted-computing-base",
            False,
            "native_decide/FFI evaluation without explicit per-occurrence approval: " + "; ".join(unapproved),
        )
    return CheckResult(
        "trusted-computing-base",
        True,
        "native_decide/FFI present but each occurrence explicitly approved; found " + "; ".join(hits),
    )


def parse_axiom_set(output: str) -> set[str]:
    """Parse a ``#print axioms`` line into its axiom set."""
    if "does not depend on any axioms" in output:
        return set()
    match = re.search(r"\[([^\]]*)\]", output)
    if not match:
        return set()
    return {a.strip() for a in match.group(1).split(",") if a.strip()}


def check_axioms(toolchain: LeanToolchain, project_dir: Path, imports: list[str], theorems: list[str]) -> CheckResult:
    """05a §3 item 3 - re-run ``#print axioms`` per theorem; axiom set must be a subset of the allowed set.

    ``theorems`` is the audit set: the manifest theorems plus every named declaration that
    pins an artefact constant by equality (obs 95, assembled in ``accept_bundle`` via
    ``named_constant_pin_theorems``) - so item 3 audits the same auditable declarations
    item 5 relies on. A named target that does not resolve under ``#print axioms`` produces
    a "no #print axioms output" violation and fails closed.

    Also catches sorryAx (item 2) and native_decide's ``Lean.ofReduceBool`` (item 4)
    as defence in depth.
    """
    outputs = toolchain.print_axioms(project_dir, imports, theorems)
    violations: list[str] = []
    for thm in theorems:
        if thm not in outputs:
            violations.append(f"{thm}: no #print axioms output")
            continue
        extra = parse_axiom_set(outputs[thm]) - ALLOWED_AXIOMS
        if extra:
            violations.append(f"{thm}: disallowed axioms {sorted(extra)}")
    if violations:
        return CheckResult("axiom-audit", False, "; ".join(violations))
    return CheckResult("axiom-audit", True, f"axiom set subset of {sorted(ALLOWED_AXIOMS)}")


def check_kernel_build(toolchain: LeanToolchain, project_dir: Path, targets: list[str] | None = None) -> CheckResult:
    """05a §3 items 0/1 - the acceptor's own clean ``lake build`` must exit 0.

    Builds the promoted modules by NAME when known (``targets``): a bare
    ``lake build`` is a no-op that exits 0 when the lakefile configures no default
    target (obs 92), which would pass this check vacuously. The producer
    ``build.log`` is never consulted here: the verdict comes only from this
    re-execution (C1).
    """
    exit_code, output = toolchain.lake_build(project_dir, targets)
    if exit_code != 0:
        return CheckResult(
            "kernel-build",
            False,
            f"lake build exit {exit_code} on acceptor re-execution; producer build.log is advisory only",
        )
    if not targets and re.search(r"no default targets|Nothing to build", output):
        return CheckResult(
            "kernel-build",
            False,
            "lake build exited 0 but built nothing (no default target and no promoted "
            "modules named to build); acceptance cannot rest on a vacuous build",
        )
    return CheckResult("kernel-build", True, "lake build exit 0 (acceptor re-execution)")


def _equality_bindings(block: str, const_name: str) -> list[tuple[str, str]]:
    """Return (operator, literal) pairs binding ``const_name`` to a numeric literal in ``block``."""
    tokens = const_name.split()
    op_alt = "|".join(re.escape(op) for op in _REL_OPS)
    pattern = re.compile(r"\s+".join(re.escape(t) for t in tokens) + rf"\s*({op_alt})\s*([0-9][0-9_]*)")
    return [(m.group(1), m.group(2).replace("_", "")) for m in pattern.finditer(block)]


def _is_kernel_checked_equality_block(block: str) -> bool:
    """True if a proof block closes with a kernel-checked tactic and no
    compiler-trust (native_decide/FFI) or hole (sorry/admit) tactic.

    05a §3 item 5 requires a constant to be pinned by a KERNEL-checked equality —
    a proof term the kernel re-verifies. `decide` is one such tactic but not the
    only one: `norm_num`/`rfl`/`simp`/`omega` are equally kernel-checked. The
    previous literal ``"decide" in block`` test wrongly excluded `norm_num`, the
    only viable tactic for the S2 greedy/pair-count constants (`Nat.ble` is
    @[extern], so `decide` stalls). native_decide and sorry/admit stay rejected.
    """
    if _NATIVE_RE.search(block) or _HOLE_RE.search(block):
        return False
    return bool(_KERNEL_TACTIC_RE.search(block))


def check_equality_obligations(
    files: dict[str, str], artefact_constants: list[dict]
) -> tuple[CheckResult, list[dict[str, object]]]:
    """05a §3 item 5 - every artefact-bound constant needs a kernel-checked ``= value`` equality.

    "Kernel-checked" means the equality is discharged by a tactic whose proof term the
    kernel re-verifies - ``decide``, ``norm_num``, ``rfl``, ``simp``, or ``omega`` - never
    ``native_decide`` (compiler trust) or ``sorry``/``admit``.

    A strict-inequality-only derivation fails (it never detects an inflated recorded
    value). A kernel value that differs from the recorded value fails AND emits a
    discrepancy record referencing the artefact ID/hash and the derived value - the
    finding does not evaporate into a silent pass.
    """
    discrepancies: list[dict[str, object]] = []
    failures: list[str] = []
    for const in artefact_constants:
        name = const["name"]
        recorded = str(const["recorded_value"])
        eq_literals: list[str] = []
        saw_inequality = False
        for text in files.values():
            for kind, _, block in iter_declarations(text):
                if kind not in ALLOWED_DECL_KINDS:
                    continue
                # Item 5 demands a KERNEL-checked equality (a proof term the kernel
                # re-verifies): decide/norm_num/rfl/simp/omega, never native_decide/sorry.
                if not _is_kernel_checked_equality_block(block):
                    continue
                for op, literal in _equality_bindings(block, name):
                    if op == "=":
                        eq_literals.append(literal)
                    else:
                        saw_inequality = True
        if eq_literals:
            if recorded in eq_literals:
                continue
            derived = eq_literals[0]
            discrepancies.append(
                {
                    "kind": "constant_equality_mismatch",
                    "constant": name,
                    "artefact_id": const.get("artefact_id"),
                    "artefact_hash": const.get("artefact_hash"),
                    "recorded_value": recorded,
                    "derived_value": derived,
                }
            )
            failures.append(f"{name}: kernel value {derived} != recorded {recorded}")
        elif saw_inequality:
            failures.append(
                f"{name}: only an inequality bound was found; item 5 requires a kernel-checked "
                "equality (= value, discharged by decide/norm_num/rfl/simp/omega)"
            )
        else:
            failures.append(f"{name}: no kernel-checked equality evaluation found")
    if failures:
        return CheckResult("constant-equality", False, "; ".join(failures)), discrepancies
    return (
        CheckResult("constant-equality", True, "every artefact-bound constant pinned by kernel-checked equality"),
        discrepancies,
    )


def named_constant_pin_theorems(files: dict[str, str], artefact_constants: list[dict]) -> list[str]:
    """Names of the NAMED (theorem/lemma) declarations that pin an artefact constant by
    ``= value`` — to be added to the ``#print axioms`` audit set (item 3).

    Closes the equality/axiom scope gap (obs 95). ``check_equality_obligations`` verifies
    a constant is pinned by a *kernel-checked* equality, but ``check_axioms`` (item 3) only
    audits the axiom footprint of the theorems named in the manifest. A constant can be
    pinned by an auxiliary ``lemma`` (§4 allows prover-authored private lemmas) that no
    manifest theorem transitively depends on; without this, that lemma's proof could invoke
    a disallowed axiom imported from the pinned external project and never be audited. By
    surfacing every *named* pin here and threading it into ``check_axioms``, the "this
    equality is kernel-checked" set and the "this equality's axioms are allowed" set cover
    the same auditable declarations.

    An anonymous ``example`` pin (the item-5 illustration in 05a §3, and the common
    fixture form) has **no name** and cannot be ``#print axioms``-queried, so it is not
    (and cannot be) covered here. Its trust rests on the acceptor's clean ``lake build``
    (the kernel re-checks the proof term), the static sorry/native_decide scans (which
    cover *all* promoted files including examples), the ``axiom``-in-promoted-files ban
    (``scan_declaration_kinds``), and — for an axiom *imported* from the pinned, hashed
    external project — the human Key-B(b) full-environment review over the independently
    authored ``statement_source``. Requiring named pins to fully mechanize that last vector
    would change item-5 admissibility and is a separate owner decision, not done here.

    Note (real toolchain): a pin name that does not resolve under ``#print axioms`` (e.g. a
    namespaced or ``private`` declaration whose queryable name differs from its source token)
    yields "no #print axioms output" in ``check_axioms`` and fails **closed** (INADMISSIBLE),
    never a silent skip.
    """
    const_names = [str(const["name"]) for const in artefact_constants]
    pins: list[str] = []
    for text in files.values():
        for kind, name, block in iter_declarations(text):
            # Only NAMED, proof-carrying, kernel-checked declarations can be axiom-audited;
            # anonymous `example` (no name) and non-proof kinds are excluded by construction.
            if kind not in ALLOWED_DECL_KINDS or kind == "example" or not name:
                continue
            if not _is_kernel_checked_equality_block(block):
                continue
            if any(op == "=" for const in const_names for op, _ in _equality_bindings(block, const)):
                pins.append(name)
    # Preserve first-seen order, drop duplicates.
    return list(dict.fromkeys(pins))


def check_witnesses(files: dict[str, str], witness_obligations: list[dict]) -> CheckResult:
    """05a §3 item 6 - each declared non-vacuity witness must be present as a named theorem/lemma.

    Whether a witness is REQUIRED (hypotheses / possibly-empty domain) is authored in
    ``statement_source`` (§4) and enumerated in ``witness_obligations``; the harness
    enforces that each named witness actually exists in the promoted set.
    """
    declared: set[str] = set()
    for text in files.values():
        for kind, name, _ in iter_declarations(text):
            if kind in ALLOWED_DECL_KINDS and name:
                declared.add(name)
    missing: list[str] = []
    for obl in witness_obligations:
        witness = obl.get("witness_example")
        if witness not in declared:
            missing.append(f"theorem {obl.get('theorem')}: witness '{witness}' not present")
    if missing:
        return CheckResult("non-vacuity-witness", False, "; ".join(missing))
    return CheckResult("non-vacuity-witness", True, "all declared non-vacuity witnesses present")


# --------------------------------------------------------------------------- #
# Bundle loading + orchestration                                              #
# --------------------------------------------------------------------------- #


def load_manifest(bundle_dir: Path) -> dict:
    """Load and minimally validate the bundle manifest (raises BundleError on any defect)."""
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        raise BundleError(f"manifest.json not found in {bundle_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BundleError(f"manifest.json is not valid JSON: {exc}") from exc
    for key in ("repo", "promoted_files", "theorems"):
        if key not in manifest:
            raise BundleError(f"manifest.json missing required key: {key}")
    if "commit" not in manifest.get("repo", {}):
        raise BundleError("manifest.json missing required key: repo.commit")
    _validate_promoted_files(bundle_dir, manifest["promoted_files"])
    return manifest


def _validate_promoted_files(bundle_dir: Path, promoted_files: object) -> None:
    """Reject malformed or unsafe promoted_files entries (fail closed before any read).

    Every entry must be an object carrying a non-empty string ``path`` that is
    relative and, once resolved, stays inside ``bundle_dir`` - so a manifest can
    neither trigger an uncaught KeyError downstream nor point the harness at an
    absolute path or a ``..`` escape outside the bundle.
    """
    if not isinstance(promoted_files, list):
        raise BundleError("manifest.json promoted_files must be a list")
    bundle_root = bundle_dir.resolve()
    for entry in promoted_files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not entry["path"]:
            raise BundleError(f"manifest.json promoted_files entry malformed (needs a string 'path'): {entry!r}")
        rel = entry["path"]
        # Catch drive/UNC (C:\..., \\host) and POSIX (/etc) absolutes on any host OS.
        if PureWindowsPath(rel).is_absolute() or PurePosixPath(rel).is_absolute():
            raise BundleError(f"manifest.json promoted_files path must be relative, not absolute: {rel}")
        resolved = (bundle_dir / rel).resolve()
        if not resolved.is_relative_to(bundle_root):
            raise BundleError(f"manifest.json promoted_files path escapes the bundle: {rel}")


def read_promoted_files(bundle_dir: Path, manifest: dict) -> dict[str, str]:
    """Read promoted-file text from disk (raises BundleError if any is missing)."""
    files: dict[str, str] = {}
    for entry in manifest["promoted_files"]:
        path = bundle_dir / entry["path"]
        if not path.is_file():
            raise BundleError(f"promoted file listed in manifest is missing: {entry['path']}")
        files[entry["path"]] = path.read_text(encoding="utf-8")
    return files


def _module_from_path(rel_path: str) -> str:
    """Derive a Lean import module name from a promoted-file path (fallback)."""
    return re.sub(r"\.lean$", "", rel_path).replace("\\", "/").replace("/", ".")


def accept_bundle(
    bundle_dir: Path | str,
    repo_commit: str,
    toolchain: LeanToolchain,
    project_dir: Path | str | None = None,
) -> AcceptanceOutcome:
    """Run every Key-A machine check against a promoted bundle by re-execution.

    Args:
        bundle_dir: Directory holding ``manifest.json``, the promoted ``.lean`` files,
            and the advisory producer artefacts.
        repo_commit: The external Lean project's commit anchor; must match the
            manifest (m3 - file hashes without a repo/commit anchor have no durable
            resolution path).
        toolchain: The acceptor's re-execution surface. Must be ``available`` or the
            harness fails closed with ``ToolchainError``.
        project_dir: The lake project root to build in; defaults to the bundle's
            ``lake_project_dir`` relative to ``bundle_dir``.

    Returns:
        An ``AcceptanceOutcome`` (admissible/inadmissible + per-item results and any
        discrepancy records).

    Raises:
        BundleError / ToolchainError: environment problems that map to EXIT_ENV_ERROR.
    """
    bundle_dir = Path(bundle_dir)
    if not bundle_dir.is_dir():
        raise BundleError(f"bundle path is not a directory: {bundle_dir}")

    manifest = load_manifest(bundle_dir)
    manifest_commit = manifest.get("repo", {}).get("commit")
    if manifest_commit != repo_commit:
        raise BundleError(f"repo-commit anchor mismatch: caller {repo_commit!r} != manifest {manifest_commit!r}")

    if not toolchain.available():
        raise ToolchainError("Lean toolchain (lake/elan) not available; cannot re-execute - failing closed")

    files = read_promoted_files(bundle_dir, manifest)
    theorems = list(manifest["theorems"])
    imports = list(manifest.get("import_modules") or [_module_from_path(e["path"]) for e in manifest["promoted_files"]])
    lake_dir = Path(project_dir) if project_dir else bundle_dir / manifest.get("lake_project_dir", ".")

    results: list[CheckResult] = []
    discrepancies: list[dict[str, object]] = []

    # Static, content-based checks (always evaluable; content is verdict).
    results.append(verify_file_integrity(bundle_dir, manifest))
    results.append(scan_holes(files))
    results.append(scan_declaration_kinds(files))
    results.append(scan_native_decide(files, manifest.get("native_decide_approved") or []))
    artefact_constants = manifest.get("artefact_constants") or []
    eq_result, eq_disc = check_equality_obligations(files, artefact_constants)
    results.append(eq_result)
    discrepancies.extend(eq_disc)
    results.append(check_witnesses(files, manifest.get("witness_obligations") or []))

    # Axiom-audit set = manifest theorems PLUS every named declaration that pins an
    # artefact constant by equality (obs 95). This makes the item-3 axiom audit cover the
    # same auditable declarations the item-5 equality check trusts, so a named auxiliary
    # lemma cannot pin a constant via a disallowed imported axiom that no manifest theorem
    # depends on. (Anonymous `example` pins have no name to audit — see
    # named_constant_pin_theorems for how their trust is established.)
    audit_theorems = list(dict.fromkeys([*theorems, *named_constant_pin_theorems(files, artefact_constants)]))

    # Dynamic re-execution (item 0 governs items 1-7). The axiom audit needs a
    # successful build first; a failed build is already inadmissible.
    build_result = check_kernel_build(toolchain, lake_dir, imports)
    results.append(build_result)
    if build_result.passed:
        results.append(check_axioms(toolchain, lake_dir, imports, audit_theorems))

    admissible = all(r.passed for r in results)
    return AcceptanceOutcome(admissible=admissible, results=results, discrepancies=discrepancies)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _outcome_to_dict(outcome: AcceptanceOutcome) -> dict[str, object]:
    return {
        "admissible": outcome.admissible,
        "failed_items": outcome.failed_items,
        "results": [{"item": r.item, "passed": r.passed, "detail": r.detail} for r in outcome.results],
        "discrepancies": outcome.discrepancies,
    }


def _print_report(outcome: AcceptanceOutcome) -> None:
    verdict = "ADMISSIBLE" if outcome.admissible else "INADMISSIBLE"
    print(f"lean_proof acceptance: {verdict}")
    for result in outcome.results:
        mark = "PASS" if result.passed else "FAIL"
        print(f"  [{mark}] {result.item}: {result.detail}")
    for disc in outcome.discrepancies:
        print(f"  [DISCREPANCY] {disc}")


def main(argv: list[str] | None = None, toolchain: LeanToolchain | None = None) -> int:
    """CLI entry point. Returns the process exit code (0/1/2)."""
    parser = argparse.ArgumentParser(
        description="Acceptor-side lean_proof verification harness (05a §3 items 0-8, Key A machine checks)."
    )
    parser.add_argument("--bundle", required=True, help="Path to the promoted lean_proof bundle directory.")
    parser.add_argument("--repo-commit", required=True, help="Commit anchor of the external Lean project (m3).")
    parser.add_argument("--project-dir", default=None, help="Lake project root to build (default: bundle).")
    parser.add_argument("--json-out", default=None, help="Write the full machine-readable outcome here.")
    parser.add_argument("--emit-discrepancies", default=None, help="Write any discrepancy records here.")
    args = parser.parse_args(argv)

    tc = toolchain if toolchain is not None else RealLeanToolchain()
    try:
        outcome = accept_bundle(
            Path(args.bundle),
            args.repo_commit,
            tc,
            Path(args.project_dir) if args.project_dir else None,
        )
    except (BundleError, ToolchainError) as exc:
        print(f"[env-error] {exc}", file=sys.stderr)
        return EXIT_ENV_ERROR

    _print_report(outcome)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(_outcome_to_dict(outcome), indent=2), encoding="utf-8")
    if outcome.discrepancies and args.emit_discrepancies:
        Path(args.emit_discrepancies).write_text(json.dumps(outcome.discrepancies, indent=2), encoding="utf-8")

    return EXIT_ADMISSIBLE if outcome.admissible else EXIT_INADMISSIBLE


if __name__ == "__main__":
    sys.exit(main())
