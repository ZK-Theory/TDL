import hashlib
import inspect
import json
import re
import subprocess
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_PATH = ROOT / ".research-system" / "packs" / "tdl-private-assurance.yaml"
CONTRACT_SCHEMA_PATH = (
    ROOT / ".research-system" / "schemas" / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json"
)
CONTRACT_SCHEMA_ID = "ars://contracts/wp6-3-tdl-private-assurance-pack"
PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"
LEGACY_GENERIC_PACK_SCHEMA_ID = "ars://assurance/assurance-pack"
LANES = {
    "topology",
    "stochastic_null",
    "statistical_panel",
    "representation",
    "output_provenance",
    "paper_claim",
}
AS_OF = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)

ACT_CONTRACT_AUTHOR = "act_00000000-0000-7000-8000-000000000001"
ACT_PRODUCER = "act_00000000-0000-7000-8000-000000000002"
ACT_REQUIREMENT_AUTHOR = "act_00000000-0000-7000-8000-000000000003"
ACT_SCOPE_REVIEWER = "act_00000000-0000-7000-8000-000000000004"
ACT_SCIENTIFIC_REVIEWER = "act_00000000-0000-7000-8000-000000000005"
ACT_OWNER = "act_00000000-0000-7000-8000-000000000006"
ACT_CONTRACT_REVIEWER = "act_00000000-0000-7000-8000-00000000000f"
ACT_SCHEMA_REVIEWER = "act_00000000-0000-7000-8000-000000000010"
ASSURANCE_PACK_ID = "asp_00000000-0000-7000-8000-000000000007"
ASSURANCE_REQUIREMENT_ID = "asr_00000000-0000-7000-8000-000000000008"
REQUIREMENT_RECORD_ID = "ard_00000000-0000-7000-8000-000000000009"
REVIEW_RECORD_ID = "arv_00000000-0000-7000-8000-00000000000a"
OWNER_DECISION_ID = "apr_00000000-0000-7000-8000-00000000000b"
SCOPE_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-00000000000d"
REVIEW_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-00000000000e"
OWNER_GRANT_ID = "agr_00000000-0000-7000-8000-00000000000c"
CONTRACT_AUTHORSHIP_RECORD_ID = "cau_00000000-0000-7000-8000-000000000011"
CONTRACT_REVIEW_RECORD_ID = "crv_00000000-0000-7000-8000-000000000012"
SCHEMA_REVIEW_RECORD_ID = "srv_00000000-0000-7000-8000-000000000013"
CONTRACT_SCHEMA_ACCEPTANCE_ID = "csa_00000000-0000-7000-8000-000000000014"
CONTRACT_REVIEW_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-000000000015"
SCHEMA_REVIEW_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-000000000016"
APPLICABILITY_CONFIRMATION_ID = "apc_00000000-0000-7000-8000-000000000017"
PRODUCER_TASK_ID = "tsk_00000000-0000-7000-8000-000000000018"
REVIEW_TASK_ID = "tsk_00000000-0000-7000-8000-000000000019"
PRODUCER_SESSION_ID = "ses_00000000-0000-7000-8000-00000000001a"
REVIEW_SESSION_ID = "ses_00000000-0000-7000-8000-00000000001b"
REVIEW_HANDOFF_ID = "hnd_00000000-0000-7000-8000-00000000001c"
CONTRACT_AUTHOR_TASK_ID = "tsk_00000000-0000-7000-8000-00000000001d"
CONTRACT_AUTHOR_SESSION_ID = "ses_00000000-0000-7000-8000-00000000001e"
CONTRACT_REVIEW_TASK_ID = "tsk_00000000-0000-7000-8000-00000000001f"
CONTRACT_REVIEW_SESSION_ID = "ses_00000000-0000-7000-8000-000000000020"
SCHEMA_REVIEW_TASK_ID = "tsk_00000000-0000-7000-8000-000000000021"
SCHEMA_REVIEW_SESSION_ID = "ses_00000000-0000-7000-8000-000000000022"

EXPECTED_EXTERNAL_SCHEMA_IDS = {
    "canonical_actor": "ars://assurance/records/canonical-actor/1.0",
    "producer_relationship_evidence": "ars://assurance/records/producer-relationship-evidence/1.0",
    "contract_schema_authorship": "ars://assurance/records/contract-schema-authorship/1.0",
    "independent_contract_review": "ars://assurance/records/independent-contract-review/1.0",
    "independent_schema_review": "ars://assurance/records/independent-schema-review/1.0",
    "stephen_contract_schema_acceptance": "ars://assurance/records/stephen-contract-schema-acceptance/1.0",
    "accepted_assurance_requirement": "ars://assurance/records/accepted-assurance-requirement/1.0",
    "obligation_applicability_confirmation": ("ars://assurance/records/obligation-applicability-confirmation/1.0"),
    "independent_pack_review": "ars://assurance/records/independent-pack-review/1.0",
    "stephen_owner_acceptance": "ars://assurance/records/stephen-owner-acceptance/1.0",
    "active_authority_grant": "ars://assurance/records/active-authority-grant/1.0",
    "registered_pack_object": "ars://assurance/records/registered-pack-object/1.0",
}

# R3-M2 remediation: the upstream contract and pack-schema content addresses are never
# hardcoded placeholders. They are resolved from the Git object store on demand by
# `_resolve_external_contract_reference()` / `_resolve_external_schema_reference()`
# (defined below, alongside the other Git-object oracle helpers), so the accepted
# identity is always the actual committed artifact and drifts automatically if the
# contract or pack schema is ever edited. Never freeze a self-hash of the contract
# into the contract's own bytes (R3-M2 self-cycle prohibition).

EXPECTED_REFERENCE_IDS = frozenset(
    """
    contract/tda-formulas/w2-exact-diagonal-bound
    contract/topology-invariants/null-operation-changes-ph-input
    contract/topology-invariants/frozen-loadings-transform-only
    contract/stochastic-tests/markov-order-provenance
    contract/stochastic-tests/monte-carlo-permutation-p-value
    contract/stage1-output-schemas/stage1-output-json-validation
    skill/validate-topology
    skill/statistical-design-audit
    skill/representation-freeze-audit
    skill/result-provenance-review
    skill/paper-claim-trace
    skill/research-assurance-triage
    """.split()
)
EXPECTED_FIXTURE_IDS = frozenset(
    """
    apf_missing_lane apf_extra_lane apf_wrong_distribution_scope
    apf_missing_authority_separation apf_producer_only_not_applicable
    apf_unversioned_reference apf_inline_reference_copy
    apf_absent_permitted_consumers apf_absent_publication_restriction
    apf_absent_path_restriction apf_absent_data_restriction
    apf_stale_pack_identity apf_expired_currency apf_cross_lane_compensation
    apf_candidate_self_acceptance apf_actor_alias
    apf_requirement_author_is_producer apf_review_subject_mismatch
    apf_owner_subject_mismatch apf_content_hash_mismatch
    apf_coordinated_contract_pack_replacement apf_consumer_widening
    apf_contradictory_distribution apf_effective_expiry_inversion
    apf_duplicate_reference_id apf_aliased_reference_id
    apf_swapped_reference_kind apf_foreign_valid_reference
    apf_pending_reference apf_dangling_lane_reference
    apf_swapped_lane_reference apf_missing_fixture apf_extra_fixture
    apf_duplicate_fixture_id apf_swapped_fixture_attack_class
    apf_missing_obligation apf_extra_obligation apf_duplicate_obligation_id
    apf_swapped_obligation_lane apf_generic_obligation_prose
    apf_unable_to_grade_pass apf_partial_pass apf_failed_proof_pass
    apf_acceptance_before_review apf_accepted_candidate_state
    apf_schema_identity_swap apf_pack_object_id_alias
    apf_producer_change_stales_requirement
    apf_reference_activation_change_stales apf_tested_object_no_op
    apf_degenerate_fallback apf_claim_escalation
    apf_representation_frozen_fallback
    """.split()
)
EXPECTED_OBLIGATION_IDS = {
    "topology": frozenset(
        """
        topology.persistence_construction_and_object topology.w2_convention
        topology.filtration_metric_order topology.threshold_truncation
        topology.landmark_rule topology.coefficient_field
        topology.homology_dimensions_and_essential_classes
        topology.benchmark_known_cases topology.scaling_and_direction
        topology.subject_topological_object_identity
        topology.interpretation_topology_geometry_association_causality
        """.split()
    ),
    "stochastic_null": frozenset(
        """
        stochastic_null.null_hypothesis_and_operation
        stochastic_null.exchangeability_conditioning
        stochastic_null.markov_order_and_strata stochastic_null.sampling_unit_and_b
        stochastic_null.rng_and_seed stochastic_null.denominator_and_p_value_formula
        stochastic_null.tested_object_mutation
        stochastic_null.independent_no_op_preflight
        stochastic_null.checkpoint_resume_equivalence
        stochastic_null.multiplicity_family
        stochastic_null.diagnostic_inferential_separation
        """.split()
    ),
    "statistical_panel": frozenset(
        """
        statistical_panel.estimand statistical_panel.target_population
        statistical_panel.eligibility_and_denominator
        statistical_panel.clustering_and_dependence
        statistical_panel.missingness_and_imputation
        statistical_panel.weights_and_trimming
        statistical_panel.variance_and_uncertainty statistical_panel.multiplicity
        statistical_panel.sensitivity statistical_panel.formula_and_software_procedure
        statistical_panel.boundary_sparse_separation_cases
        statistical_panel.descriptive_associational_predictive_causal_limits
        """.split()
    ),
    "representation": frozenset(
        """
        representation.fit_transform_authority
        representation.frozen_model_loadings_scaler_labels
        representation.training_population representation.state_recoding
        representation.windows_dimensions_and_vintage representation.fingerprint_hash
        representation.transform_only
        representation.comparability_across_waves_cohorts_subgroups
        representation.prohibited_refit_and_fallback
        representation.uncertainty_and_sensitivity
        """.split()
    ),
    "output_provenance": frozenset(
        """
        output_provenance.immutable_object_and_input_ids_hashes
        output_provenance.code_and_environment
        output_provenance.parameters_seeds_and_sample_restrictions
        output_provenance.roots_and_date_suffix output_provenance.no_overwrite
        output_provenance.schema_cache_lineage_and_regenerability
        output_provenance.consumer_required_comparison_fields
        output_provenance.scoped_supersession_and_retention
        output_provenance.exact_accepted_bytes_validation
        output_provenance.vault_and_claim_routing_authorization
        output_provenance.consumer_publication_path_data_boundaries
        """.split()
    ),
    "paper_claim": frozenset(
        """
        paper_claim.exact_accepted_result_and_evidence_ids_hashes
        paper_claim.governing_decision_rule_and_outcome paper_claim.proposed_wording
        paper_claim.claim_type_and_strength paper_claim.population_and_domain_scope
        paper_claim.uncertainty paper_claim.limitations_and_disclosure
        paper_claim.negative_and_partial_restrictions
        paper_claim.independent_claim_review
        paper_claim.stephen_attributed_promotion_decision
        paper_claim.no_causal_escalation paper_claim.no_novelty_escalation
        paper_claim.no_generality_escalation
        paper_claim.result_acceptance_and_claim_promotion_separation
        """.split()
    ),
}


class CandidatePackError(ValueError):
    """A relational or external-authority violation outside JSON Schema."""


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(SCHEMAS)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _git_blob_id(data: bytes) -> str:
    return subprocess.check_output(["git", "hash-object", "--stdin"], input=data).decode().strip()


def _git_blob_id_without_filters(data: bytes) -> str:
    return subprocess.check_output(["git", "hash-object", "--no-filters", "--stdin"], input=data).decode().strip()


def _repo_relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _git_head_blob_id(repo_relative_path: str) -> str:
    """Resolve the frozen HEAD blob OID for a committed repo-relative path."""
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{repo_relative_path}"], cwd=ROOT).decode().strip()


def _git_blob_bytes(blob_oid: str) -> bytes:
    return subprocess.check_output(["git", "cat-file", "blob", blob_oid], cwd=ROOT)


def _resolve_committed_bytes(path: Path, *, working_tree_bytes: bytes | None = None) -> tuple[bytes, str]:
    """Resolve a committed file's exact frozen bytes through the Git-object oracle.

    R3-M1: identity is established from ``git rev-parse HEAD:<path>`` plus
    ``git cat-file blob <oid>`` — the frozen LF Git-object bytes — never from
    ``Path.read_bytes()``, which returns whatever the current checkout's clean/smudge
    filters produced (CRLF under ``core.autocrlf=true``) and is therefore not portable
    across checkouts even though ``git status`` reports clean.

    Separately (and this is a distinct check, not folded into content-identity
    resolution): the working-tree copy must still match HEAD once Git's own clean
    filter is applied to it (``git hash-object --path``, which reproduces exactly what
    a commit would hash for this path). A real CRLF *checkout* of an LF blob resolves
    identically to HEAD here (the filter renormalizes it), so it is not flagged; a
    genuinely dirty/uncommitted edit is not equal to HEAD under the filter either and
    is rejected with its own diagnostic, independent of the frozen bytes returned.

    ``working_tree_bytes`` lets callers (tests) supply an alternate working-tree
    representation without touching the real file on disk, to exercise the CRLF vs.
    dirty distinction deterministically.
    """
    repo_relative_path = _repo_relative_path(path)
    head_blob = _git_head_blob_id(repo_relative_path)
    raw_working_tree_bytes = path.read_bytes() if working_tree_bytes is None else working_tree_bytes
    working_tree_blob = (
        subprocess.check_output(
            ["git", "hash-object", "--path", repo_relative_path, "--stdin"],
            input=raw_working_tree_bytes,
            cwd=ROOT,
        )
        .decode()
        .strip()
    )
    if working_tree_blob != head_blob:
        raise CandidatePackError(f"dirty or uncommitted working-tree bytes: {repo_relative_path}")
    return _git_blob_bytes(head_blob), head_blob


@lru_cache(maxsize=1)
def _resolve_external_contract_reference() -> dict:
    """Independently resolve the upstream contract's exact committed content address.

    R3-M2: this is never read from the candidate or from the contract's own embedded
    fields (which would be a self-hash cycle) — it is derived fresh from the Git object
    store for ``CONTRACT_PATH`` each time the cache is populated, so it always names
    the actual committed artifact.
    """
    subject = _resolve_current_repository_subject(CONTRACT_PATH)
    contract_blob = subject["git_blob"]
    contract_bytes = _git_blob_bytes(contract_blob)
    return {
        "schema_id": CONTRACT_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": _repo_relative_path(CONTRACT_PATH),
        "git_blob": contract_blob,
        "canonical_sha256": hashlib.sha256(contract_bytes).hexdigest(),
    }


@lru_cache(maxsize=1)
def _resolve_external_schema_reference() -> dict:
    """Independently resolve the TDL-private pack schema's exact committed content address."""
    pack_schema_path = SCHEMAS / "assurance" / "assurance-pack.schema.json"
    schema_bytes, schema_blob = _resolve_committed_bytes(pack_schema_path)
    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": _repo_relative_path(pack_schema_path),
        "git_blob": schema_blob,
        "canonical_sha256": hashlib.sha256(schema_bytes).hexdigest(),
    }


def _raw_contract_bytes(contract: dict) -> bytes:
    raw = yaml.safe_dump(contract, sort_keys=False, allow_unicode=True, width=4096).encode("utf-8")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    return raw


ContractAuthorityResolver = Callable[[], tuple[bytes, str]]
_FIXTURE_AUTHORITY_ISSUER = object()
_FIXTURE_RECORD_AUTHORITY_ISSUER = object()
AUTHORITY_SOURCE_IDS = frozenset({"source.w1_v0_3", "source.w2_v0_3"})
AUTHORITY_PHASES = ("load", "acceptance", "consumption")


@dataclass(frozen=True)
class _FixtureContractAuthority:
    raw_contract_bytes: bytes
    contract_blob: str
    issuer: object

    def __call__(self) -> tuple[bytes, str]:
        return self.raw_contract_bytes, self.contract_blob


def _fixture_contract_authority(contract: dict) -> _FixtureContractAuthority:
    """Freeze a hypothetical contract behind an explicit test-only trust seam."""
    raw_contract_bytes = _raw_contract_bytes(contract)
    contract_blob = _git_blob_id_without_filters(raw_contract_bytes)
    return _FixtureContractAuthority(raw_contract_bytes, contract_blob, _FIXTURE_AUTHORITY_ISSUER)


def _require_issued_fixture_authority(authority: _FixtureContractAuthority) -> None:
    if not isinstance(authority, _FixtureContractAuthority) or authority.issuer is not _FIXTURE_AUTHORITY_ISSUER:
        raise CandidatePackError("hypothetical contract authority was not issued by the fixture factory")


@dataclass(frozen=True)
class _AuthoritySnapshot:
    snapshot_id: str
    authority_root_sha256: str
    w1_w2_authority_subjects: dict[str, dict]
    record_store: dict[str, dict]
    record_hashes: dict[str, str]
    reference_subjects: dict[str, dict]


@dataclass
class _FixtureRecordAuthority:
    snapshots: tuple[_AuthoritySnapshot, ...]
    issuer: object
    call_count: int = 0

    def __call__(self, phase: str) -> _AuthoritySnapshot:
        if phase not in AUTHORITY_PHASES:
            raise CandidatePackError(f"unsupported authority resolution phase: {phase}")
        index = min(self.call_count, len(self.snapshots) - 1)
        self.call_count += 1
        return deepcopy(self.snapshots[index])


def _resolve_current_repository_subject(path: Path) -> dict:
    """Resolve current working-tree bytes through Git's configured clean filter.

    ``git hash-object -w`` intentionally persists the filtered blob in the local
    object database so the returned object ID can be read back as canonical bytes.
    CI therefore gains one unreachable blob per distinct working-tree candidate.
    """
    repo_relative_path = _repo_relative_path(path)
    working_tree_bytes = path.read_bytes()
    # Persistence is intentional: the subsequent read must use Git's canonical blob,
    # not the checkout representation supplied by the filesystem.
    blob_oid = (
        subprocess.check_output(
            ["git", "hash-object", "-w", "--path", repo_relative_path, "--stdin"],
            input=working_tree_bytes,
            cwd=ROOT,
        )
        .decode()
        .strip()
    )
    canonical_bytes = _git_blob_bytes(blob_oid)
    return {
        "repository_path": repo_relative_path,
        "git_blob": blob_oid,
        "canonical_blob_bytes": canonical_bytes,
        "canonical_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
    }


def _current_reference_subjects(contract: dict) -> dict[str, dict]:
    subjects = {}
    for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]:
        resolved = _resolve_current_repository_subject(ROOT / row["repository_path"])
        subjects[row["reference_id"]] = {
            key: resolved[key] for key in ("repository_path", "git_blob", "canonical_sha256")
        }
    return subjects


def _validate_reference_semantic_compatibility(contract: dict) -> None:
    """Verify pinned skill and formula-contract semantics remain compatible.

    Args:
        contract: The trusted, schema-validated assurance contract whose
            ``exact_reference_rows`` pin the skill and formula-contract paths.

    Raises:
        CandidatePackError: If required terms are missing, forbidden semantics
            are present, or the pinned formula contract has drifted.
    """
    reference_rows = {
        row["reference_id"]: row for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]
    }
    skill_path = ROOT / reference_rows["skill/validate-topology"]["repository_path"]
    formula_path = ROOT / reference_rows["contract/stochastic-tests/monte-carlo-permutation-p-value"]["repository_path"]
    skill_text = skill_path.read_text(encoding="utf-8")
    formula_contract = _load_yaml(formula_path)
    required_skill_terms = ("p = (r + 1) / (n + 1)", "pvalue_null_draws", "effect_null_pairs")
    forbidden_skill_patterns = [
        invariant["expression"].removeprefix("forbidden_skill_regex:")
        for invariant in formula_contract["formula"]["invariants"]
        if invariant["expression"].startswith("forbidden_skill_regex:")
    ]
    if (
        formula_contract["formula"]["expression"] != "p = (r + 1) / (n + 1)"
        or len(forbidden_skill_patterns) != 2
        or any(term not in skill_text for term in required_skill_terms)
        or any(re.search(pattern, skill_text, flags=re.IGNORECASE) for pattern in forbidden_skill_patterns)
    ):
        raise CandidatePackError("current reference snapshot is semantically incompatible with the pinned p-value")


def _authority_snapshot(
    contract: dict,
    record_store: dict[str, dict],
    record_hashes: dict[str, str],
    *,
    snapshot_id: str = "auth_00000000-0000-7000-8000-000000000001",
    reference_subjects: dict[str, dict] | None = None,
) -> _AuthoritySnapshot:
    source_rows = {
        row["source_id"]: {key: row[key] for key in ("repository_path", "git_commit", "git_blob", "canonical_sha256")}
        for row in contract["source_authority"]["governing_sources"]
        if row["source_id"] in AUTHORITY_SOURCE_IDS
    }
    references = reference_subjects or _current_reference_subjects(contract)
    root_preimage = {
        "snapshot_id": snapshot_id,
        "w1_w2_authority_subjects": source_rows,
        "record_hashes": record_hashes,
        "reference_subjects": references,
    }
    return _AuthoritySnapshot(
        snapshot_id=snapshot_id,
        authority_root_sha256=_canonical_sha256(root_preimage),
        w1_w2_authority_subjects=deepcopy(source_rows),
        record_store=deepcopy(record_store),
        record_hashes=deepcopy(record_hashes),
        reference_subjects=deepcopy(references),
    )


def _fixture_record_authority(
    contract: dict,
    record_store: dict[str, dict],
    record_hashes: dict[str, str],
    *,
    snapshots: tuple[_AuthoritySnapshot, ...] | None = None,
) -> _FixtureRecordAuthority:
    issued_snapshots = snapshots or (_authority_snapshot(contract, record_store, record_hashes),)
    return _FixtureRecordAuthority(issued_snapshots, _FIXTURE_RECORD_AUTHORITY_ISSUER)


def _resolve_authority_phase(
    authority_resolver: _FixtureRecordAuthority,
    phase: str,
    contract: dict,
    *,
    expected_root: str | None = None,
) -> _AuthoritySnapshot:
    if (
        not isinstance(authority_resolver, _FixtureRecordAuthority)
        or authority_resolver.issuer is not _FIXTURE_RECORD_AUTHORITY_ISSUER
    ):
        raise CandidatePackError("trusted authority resolver was not supplied by the W1/W2 application root")
    snapshot = authority_resolver(phase)
    expected_sources = {
        row["source_id"]: {key: row[key] for key in ("repository_path", "git_commit", "git_blob", "canonical_sha256")}
        for row in contract["source_authority"]["governing_sources"]
        if row["source_id"] in AUTHORITY_SOURCE_IDS
    }
    if set(expected_sources) != AUTHORITY_SOURCE_IDS or snapshot.w1_w2_authority_subjects != expected_sources:
        raise CandidatePackError("authority root is not bound to the accepted W1/W2 authority surface")
    root_preimage = {
        "snapshot_id": snapshot.snapshot_id,
        "w1_w2_authority_subjects": snapshot.w1_w2_authority_subjects,
        "record_hashes": snapshot.record_hashes,
        "reference_subjects": snapshot.reference_subjects,
    }
    if snapshot.authority_root_sha256 != _canonical_sha256(root_preimage):
        raise CandidatePackError("trusted authority root does not bind its resolved content")
    if expected_root is not None and snapshot.authority_root_sha256 != expected_root:
        raise CandidatePackError("authority changed during load, acceptance, or consumption revalidation")
    contract_references = {
        row["reference_id"]: {key: row[key] for key in ("repository_path", "git_blob", "canonical_sha256")}
        for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]
    }
    if snapshot.reference_subjects != contract_references:
        raise CandidatePackError(f"current reference snapshot differs during {phase}")
    _validate_reference_semantic_compatibility(contract)
    return snapshot


def _resolve_contract_authority(
    trusted_contract_resolver: ContractAuthorityResolver | None = None,
) -> tuple[bytes, dict, dict]:
    """Resolve contract bytes from Git, or an explicit trusted hypothetical-fixture seam."""
    if trusted_contract_resolver is None:
        current_subject = _resolve_current_repository_subject(CONTRACT_PATH)

        def resolver() -> tuple[bytes, str]:
            return current_subject["canonical_blob_bytes"], current_subject["git_blob"]

    else:
        resolver = trusted_contract_resolver
    raw_contract_bytes, trusted_contract_blob = resolver()
    computed_contract_blob = _git_blob_id_without_filters(raw_contract_bytes)
    if computed_contract_blob != trusted_contract_blob:
        raise CandidatePackError("trusted contract resolver returned bytes outside its Git-blob authority")
    parsed = yaml.safe_load(raw_contract_bytes.decode("utf-8"))
    _schema_registry().validate(CONTRACT_SCHEMA_ID, parsed)
    subject = {
        "schema_id": CONTRACT_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": _repo_relative_path(CONTRACT_PATH),
        "git_blob": trusted_contract_blob,
        "canonical_sha256": hashlib.sha256(raw_contract_bytes).hexdigest(),
    }
    return raw_contract_bytes, parsed, subject


def _raw_pack_bytes(pack: dict, *, leading_comment: str | None = None, reverse_top_level: bool = False) -> bytes:
    value = dict(reversed(list(pack.items()))) if reverse_top_level else pack
    rendered = yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=4096)
    if leading_comment is not None:
        rendered = f"# {leading_comment}\n{rendered}"
    raw = rendered.encode("utf-8")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    return raw


def _parse_candidate_pack_bytes(raw_candidate_pack_bytes: bytes) -> dict:
    if b"\r" in raw_candidate_pack_bytes or not raw_candidate_pack_bytes.endswith(b"\n"):
        raise CandidatePackError("candidate bytes must be exact UTF-8/LF with terminal LF")
    try:
        decoded = raw_candidate_pack_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidatePackError("candidate bytes must be exact UTF-8/LF with terminal LF") from exc
    parsed = yaml.safe_load(decoded)
    if not isinstance(parsed, dict):
        raise CandidatePackError("candidate bytes must parse to one pack object")
    _schema_registry().validate(PACK_SCHEMA_ID, parsed)
    return parsed


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CandidatePackError("timestamp must include timezone")
    return parsed


def _assert_all_object_schemas_are_closed(schema: dict) -> None:
    stack = [("<root>", schema)]
    seen_objects = 0
    while stack:
        location, node = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "object":
                seen_objects += 1
                assert node.get("additionalProperties") is False, location
            stack.extend((f"{location}/{key}", value) for key, value in node.items())
        elif isinstance(node, list):
            stack.extend((f"{location}/{index}", value) for index, value in enumerate(node))
    assert seen_objects > 20


@lru_cache(maxsize=1)
def _external_schema_artifact() -> tuple[dict, str, str]:
    """Resolve and parse the external schema through the current Git-filtered blob.

    ``_resolve_current_repository_subject`` filters the working-tree bytes and
    returns the canonical Git object bytes for JSON parsing. This remains portable
    across CRLF and LF checkout representations.
    """
    subject = _resolve_current_repository_subject(CONTRACT_SCHEMA_PATH)
    schema_blob = subject["git_blob"]
    schema_bytes = subject["canonical_blob_bytes"]
    schema_document = json.loads(schema_bytes.decode("utf-8"))
    Draft202012Validator.check_schema(schema_document)
    return schema_document, schema_blob, subject["canonical_sha256"]


@lru_cache(maxsize=1)
def _external_root_validator() -> Draft202012Validator:
    return Draft202012Validator(_external_schema_artifact()[0], format_checker=Draft202012Validator.FORMAT_CHECKER)


def _external_schema_catalogue(contract: dict) -> tuple[dict, dict[str, dict]]:
    catalogue = contract["required_pack_contract"]["external_record_schema_catalogue"]
    schema_document, schema_blob, schema_sha256 = _external_schema_artifact()
    rows = _rows_by_id(catalogue["exact_schema_rows"], "record_class", "external schema")
    if set(rows) != set(EXPECTED_EXTERNAL_SCHEMA_IDS):
        raise CandidatePackError("external record schema class closure differs")
    if catalogue["exact_schema_count"] != len(rows):
        raise CandidatePackError("external record schema count differs")
    for record_class, row in rows.items():
        if row["record_type"] != record_class:
            raise CandidatePackError("external record class/type binding differs")
        if row["schema_id"] != EXPECTED_EXTERNAL_SCHEMA_IDS[record_class] or row["schema_version"] != "1.0.0":
            raise CandidatePackError("external record schema identity differs")
        if row["repository_path"] != catalogue["schema_document_repository_path"]:
            raise CandidatePackError("external record schema path differs")
        if row["schema_git_blob"] != schema_blob or row["schema_canonical_sha256"] != schema_sha256:
            raise CandidatePackError("external record schema content identity differs")
        definition_name = row["schema_json_pointer"].removeprefix("#/$defs/")
        external_schema = schema_document["$defs"].get(definition_name)
        if external_schema is None:
            raise CandidatePackError("external record schema pointer is unresolved")
        if (
            external_schema.get("$id") != row["schema_id"]
            or external_schema.get("x-schema-version") != row["schema_version"]
        ):
            raise CandidatePackError("external record schema pointer identity differs")
    return schema_document, rows


def _validate_external_record(contract: dict, record: dict, record_class: str) -> None:
    schema_document, rows = _external_schema_catalogue(contract)
    row = rows[record_class]
    definition_name = row["schema_json_pointer"].removeprefix("#/$defs/")
    root_validator = _external_root_validator()
    errors = sorted(
        root_validator.evolve(schema=schema_document["$defs"][definition_name]).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        message = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
        )
        raise CandidatePackError(f"invalid {record_class} record: {message}")


def _rows_by_id(rows: list[dict], id_field: str, label: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        row_id = row[id_field]
        if row_id in indexed:
            raise CandidatePackError(f"duplicate {label} id: {row_id}")
        indexed[row_id] = row
    return indexed


def _derived_pending_reference_ids(contract: dict) -> set[str]:
    references = contract["required_pack_contract"]["references"]
    rows = references["exact_reference_rows"]
    acceptance_active_states = set(references["acceptance_active_states"])
    return {
        row["reference_id"]
        for row in rows
        if row["activation_state"] not in acceptance_active_states or not row["pack_acceptance_eligible"]
    }


def _validate_pending_reference_relation(contract: dict) -> None:
    observed = contract["required_pack_contract"]["references"]["current_pending_reference_ids"]
    expected = _derived_pending_reference_ids(contract)
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise CandidatePackError("current pending reference relation differs from derived exact set")


def _validate_lane_enforcer_relation(pack: dict, observed_references: dict[str, dict]) -> None:
    for lane_id, lane in pack["lanes"].items():
        governing = set(lane["governing_reference_ids"])
        for obligation in lane["obligation_rows"]:
            for reference_id in obligation["enforcing_reference_ids"]:
                if reference_id not in governing:
                    raise CandidatePackError("obligation enforcer is omitted from lane governing relation")
                reference = observed_references.get(reference_id)
                if reference is None or lane_id not in reference["allowed_lane_ids"]:
                    raise CandidatePackError("obligation enforcer is foreign or not permitted for lane")


def _expanded_obligation(row: dict, profile: dict) -> dict:
    return {
        "obligation_id": row["obligation_id"],
        "row_profile_id": profile["row_profile_id"],
        "source_authority_id": profile["source_authority_id"],
        "source_sections": deepcopy(row["source_sections"]),
        "assertion_classes": deepcopy(row["assertion_classes"]),
        "enforcing_reference_ids": deepcopy(row["enforcing_reference_ids"]),
        "review_question_id": row["review_question_id"],
        "evidence_output_id": row["evidence_output_id"],
    }


def _proposed_pack(contract: dict | None = None, *, contract_subject: dict | None = None) -> dict:
    contract = deepcopy(contract or _load_yaml(CONTRACT_PATH))
    required = contract["required_pack_contract"]
    reference_rows = required["references"]["exact_reference_rows"]
    contract_references = [deepcopy(row) for row in reference_rows if row["reference_kind"] == "contract"]
    skill_references = [deepcopy(row) for row in reference_rows if row["reference_kind"] == "skill"]
    profile = required["obligation_row_profile"]
    lanes = {}
    for lane_id, lane_contract in required["lanes"].items():
        lanes[lane_id] = {
            "lane_id": lane_id,
            "governing_reference_ids": deepcopy(lane_contract["exact_governing_reference_ids"]),
            "obligation_rows": [_expanded_obligation(row, profile) for row in lane_contract["required_obligations"]],
            "fixture_ids": deepcopy(lane_contract["exact_fixture_ids"]),
            "prospective_schema_only": True,
            "scientific_review_status": "not_performed_by_pack_schema",
            "failure_consequence": "blocked_no_cross_lane_compensation",
            "cross_lane_compensation": "prohibited",
        }
    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "pack_id": "TDL_private",
        "assurance_pack_id": ASSURANCE_PACK_ID,
        "assurance_pack_revision": 1,
        "canonical_repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "distribution_scope": "TDL_private",
        "candidate_state": "proposed",
        "producer_actor_id": ACT_PRODUCER,
        "upstream_contract_reference": deepcopy(contract_subject or _resolve_external_contract_reference()),
        "schema_reference": deepcopy(_resolve_external_schema_reference()),
        "assurance_requirement_reference": {
            "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
            "revision": 1,
            "acceptance_record_id": REQUIREMENT_RECORD_ID,
            "acceptance_record_sha256": "6" * 64,
            "prospective_producer_actor_id": ACT_PRODUCER,
        },
        "source_authority": {
            "accepted_plan_revision": contract["source_authority"]["accepted_plan_revision"],
            "governing_sources": deepcopy(contract["source_authority"]["governing_sources"]),
        },
        "references": {
            "contract_references": contract_references,
            "skill_references": skill_references,
        },
        "task_applicability_policy": {
            "pack_obligations": "all_required",
            "task_not_applicable_location": "external_accepted_assurance_requirement",
            "producer_only_confirmation": "prohibited",
            "minimum_independence_grade": "I2",
            "unable_to_grade_may_pass": False,
            "partial_may_pass": False,
            "failed_proof_may_pass": False,
        },
        "distribution_controls": {
            "permitted_consumers": deepcopy(required["distribution"]["exact_permitted_consumers"]),
            "public_template_export": "prohibited",
            "publication_boundary": {
                "public_template_use": "prohibited",
                "manuscript_use": "requires_separately_accepted_result_and_claim_decision",
                "public_excerpt": "prohibited_without_template_safe_derivative_review",
                "claim_promotion": "requires_stephen_attributed_p005_decision",
            },
            "path_restrictions": {
                "repository_namespace": "tdl_private_only",
                "public_repository_paths": "prohibited",
                "public_template_paths": "prohibited",
                "private_path_disclosure": "opaque_content_addressed_references_only",
            },
            "data_restrictions": {
                "raw_restricted_data": "prohibited",
                "minimized_excerpts": "separately_authorized_only",
                "restricted_references": "opaque_content_addressed_only",
                "secrets_env_transcripts_hidden_reasoning": "prohibited",
            },
        },
        "currency": {
            "authored_at": "2026-07-18T09:00:00Z",
            "effective_at": "2026-07-18T09:15:00Z",
            "expires_at": "2027-07-18T09:00:00Z",
            "currency_triggers": [
                "upstream_contract_identity_changed",
                "schema_identity_changed",
                "reference_identity_or_activation_changed",
                "assurance_requirement_or_producer_relationship_changed",
                "distribution_or_consumer_policy_changed",
            ],
            "retention_class": "durable_governance_record",
            "stale_identity_behavior": "block_consumption_and_require_superseding_revision",
        },
        "lanes": lanes,
        "required_fixtures": deepcopy(required["fixtures"]["exact_fixture_rows"]),
        "limitations": [
            "prospective_pack_no_result_or_claim_review",
            "schema_shape_does_not_establish_scientific_validity",
            "candidate_cannot_assert_review_or_owner_acceptance",
            "pending_reference_blocks_owner_acceptance",
        ],
        "core_boundary": {
            "may_modify_w1_w2_lifecycle": False,
            "may_modify_canonical_authority": False,
            "may_override_p005_p022": False,
            "may_lower_w3_w4_controls": False,
            "may_assert_observed_results": False,
            "may_accept_results": False,
            "may_promote_claims": False,
            "may_authorize_migration": False,
        },
    }


def _assert_test_surface_closure(bindings: dict, defined_names: set[str] | None = None) -> None:
    """Assert the contract's declared test surface is closed over this module's test functions.

    Enforces the two real guarantees separately rather than collapsing them into one equality:

    - **no undeclared test** — ``defined <= declared`` fails closed, so a control cannot be
      added without being declared;
    - **no silent shrinkage of a durable control** — ``durable <= defined`` fails closed, so a
      declared durable control cannot be deleted.

    It deliberately permits a **task-local** declared name to be absent once its task has ended.
    That is what task-local means, and it matches the contract's own declared constant,
    ``every_defined_test_function_is_declared_durable_or_task_local`` — defined ⊆ declared.

    The previous equality assertion was stricter than the semantics the accepted contract
    declares. Because the contract is accepted at exact bytes, that extra strictness froze every
    task-local scope marker permanently: the successor task the contract anticipates could not
    create the artifact, delete the expired marker, or amend the declaration. Amending this is a
    correction to match the declared constant, not a weakening — both guarantees above still hold.

    Shared by the strict-pending contract test and the dedicated closure test so the two cannot
    drift apart; both pass `contract["validation_bindings"]`.

    Args:
        bindings: The contract's ``validation_bindings`` block.
        defined_names: Test-function names to check against. Defaults to this module's own
            surface; injectable so the semantics themselves can be given negative controls
            (see ``test_tdl_private_pack_candidate.py``), which reading ``globals()``
            unconditionally made impossible.
    """
    bound_names = set(bindings["durable_test_functions"])
    task_local_names = set(bindings["task_local_unbound_test_functions"])
    assert not bound_names & task_local_names
    assert bindings["binding_closure"] == "every_defined_test_function_is_declared_durable_or_task_local"
    if defined_names is None:
        defined_names = {name for name, value in globals().items() if name.startswith("test_") and callable(value)}
    declared_test_functions = bound_names | task_local_names
    assert (
        defined_names <= declared_test_functions
    ), f"undeclared test functions: {sorted(defined_names - declared_test_functions)}"
    assert bound_names <= defined_names, f"declared durable control is missing: {sorted(bound_names - defined_names)}"


def _review_operator_provenance(
    *,
    producer_actor_id: str,
    reviewer_actor_id: str,
    review_task_id: str,
    review_session_id: str,
    producer_task_id: str = CONTRACT_AUTHOR_TASK_ID,
    producer_session_id: str = CONTRACT_AUTHOR_SESSION_ID,
    producer_operator_type: str = "codex_task_agent",
    reviewer_operator_type: str = "codex_task_agent",
    session_family: str = "codex_standalone",
    handoff_id: str = REVIEW_HANDOFF_ID,
) -> dict:
    """Build a typed operator-provenance block for any of the three review record types."""
    return {
        "producer_operator": {"actor_id": producer_actor_id, "operator_type": producer_operator_type},
        "reviewer_operator": {"actor_id": reviewer_actor_id, "operator_type": reviewer_operator_type},
        "producer_task_id": producer_task_id,
        "review_task_id": review_task_id,
        "producer_session_id": producer_session_id,
        "review_session_id": review_session_id,
        "handoff_id": handoff_id,
        "session_family": session_family,
        "context_mode": "fresh_task_no_parent_history",
        "fork_turns": "none",
    }


def _validate_review_operator_provenance(
    contract: dict,
    review: dict,
    *,
    producer_actor_id: str,
    reviewer_actor_id: str,
    label: str,
) -> dict:
    """Check one review record's typed operator provenance against the contract's operator model.

    The contract binds `review_provenance_binding` at `external_acceptance_evidence` level, which
    governs every entry of `review_provenance_required_record_types` — so the same check applies to
    the contract review, the schema review, and the pack review, not only the pack review.
    """
    evidence = contract["required_pack_contract"]["external_acceptance_evidence"]
    operator_model = evidence["operator_model"]
    allowed_session_families = set(operator_model["allowed_session_families"])
    # Derive the permitted review-operator types from the contract's own prohibitions rather than
    # equating them with the agent allowlist. The two are the same set only while
    # review_operator_must_be_agent_operator_type is true and human_owner is barred; reading the
    # flags keeps the check correct if either is ever relaxed, instead of silently ignoring them.
    allowed_operator_types = set(operator_model["allowed_agent_operator_types"])
    if not operator_model["review_operator_must_be_agent_operator_type"]:
        allowed_operator_types |= {"human_owner"}
    if operator_model["human_owner_may_act_as_review_operator"]:
        allowed_operator_types |= {"human_owner"}
    elif "human_owner" in allowed_operator_types:
        allowed_operator_types.discard("human_owner")
    provenance = review["operator_provenance"]
    producer_operator = provenance["producer_operator"]
    reviewer_operator = provenance["reviewer_operator"]
    if (
        producer_operator["actor_id"] != producer_actor_id
        or reviewer_operator["actor_id"] != reviewer_actor_id
        or producer_operator["operator_type"] not in allowed_operator_types
        or reviewer_operator["operator_type"] not in allowed_operator_types
        or provenance["session_family"] not in allowed_session_families
        or provenance["producer_task_id"] == provenance["review_task_id"]
        or provenance["producer_session_id"] == provenance["review_session_id"]
        or provenance["context_mode"] != "fresh_task_no_parent_history"
        or provenance["fork_turns"] != "none"
    ):
        raise CandidatePackError(f"{label} review task provenance does not prove a separate fresh context")
    return provenance


def _eligible_contract() -> dict:
    contract = _load_yaml(CONTRACT_PATH)
    replacement_digits = iter("789a")
    for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]:
        if row["reference_kind"] == "contract" and not row["pack_acceptance_eligible"]:
            digit = next(replacement_digits)
            row["activation_state"] = "active"
            row["pack_acceptance_eligible"] = True
            row["git_blob"] = digit * 40
            row["canonical_sha256"] = digit * 64
    contract["required_pack_contract"]["references"]["current_pending_reference_ids"] = []
    return contract


def _validate_proposed_pack_with_authority(
    pack: dict,
    *,
    contract: dict | None = None,
    trusted_contract_resolver: ContractAuthorityResolver | None = None,
    require_active_references: bool = False,
    registered_pack_ids: frozenset[str] = frozenset({ASSURANCE_PACK_ID}),
    as_of: datetime = AS_OF,
) -> None:
    _, parsed_contract, accepted_contract_subject = _resolve_contract_authority(trusted_contract_resolver)
    contract = contract or parsed_contract
    if contract != parsed_contract:
        raise CandidatePackError("supplied contract differs from trusted Git contract authority")
    _schema_registry().validate(CONTRACT_SCHEMA_ID, contract)
    _schema_registry().validate(PACK_SCHEMA_ID, pack)
    _validate_pending_reference_relation(contract)
    _external_schema_catalogue(contract)
    if pack["upstream_contract_reference"] != accepted_contract_subject:
        raise CandidatePackError("stale upstream contract subject")
    if pack["schema_reference"] != _resolve_external_schema_reference():
        raise CandidatePackError("stale pack schema subject")
    if pack["assurance_pack_id"] not in registered_pack_ids:
        raise CandidatePackError("assurance_pack_id is not registered by W1 authority")
    if pack["assurance_requirement_reference"]["prospective_producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("prospective producer relationship is stale")
    expected_source_authority = {
        "accepted_plan_revision": contract["source_authority"]["accepted_plan_revision"],
        "governing_sources": contract["source_authority"]["governing_sources"],
    }
    if pack["source_authority"] != expected_source_authority:
        raise CandidatePackError("stale or incomplete source authority")

    required = contract["required_pack_contract"]
    expected_references = _rows_by_id(required["references"]["exact_reference_rows"], "reference_id", "reference")
    observed_reference_rows = pack["references"]["contract_references"] + pack["references"]["skill_references"]
    observed_references = _rows_by_id(observed_reference_rows, "reference_id", "reference")
    if observed_references != expected_references:
        raise CandidatePackError("reference rows must equal the exact upstream set")
    if set(observed_references) != EXPECTED_REFERENCE_IDS:
        raise CandidatePackError("reference ID closure differs from the independent fixture")
    # Bind the declared per-kind reference counts. Previously read by nothing, so the contract could
    # claim 6 and 6 while carrying any number.
    #
    # Per-entry reference_kind is deliberately not re-checked here: the pack schema already
    # constrains each list to its own kind, and more strictly than a kind comparison would — it
    # pins reference_kind, the reference_id pattern, the repository_path pattern, and
    # activation_state per list, and rejects a swap before this validator runs. A duplicate check
    # here would be unreachable, so it could never be given a watched negative.
    references_contract = contract["required_pack_contract"]["references"]
    if len(pack["references"]["contract_references"]) != references_contract["required_contract_reference_count"]:
        raise CandidatePackError("contract reference count differs from the declared requirement")
    if len(pack["references"]["skill_references"]) != references_contract["required_skill_reference_count"]:
        raise CandidatePackError("skill reference count differs from the declared requirement")
    # The boundary fixture set is declared in three places. Nothing compared them, and one of the
    # three was pinned as literals in a test, so two copies could drift apart while every check
    # passed. Require agreement rather than collapsing them, which would change contract shape.
    boundary = contract["required_pack_contract"]["fixture_execution_boundary"]
    boundary_copies = {
        "required_executed_boundary_fixture_ids": frozenset(
            contract["required_pack_contract"]["external_acceptance_evidence"]["required_executed_boundary_fixture_ids"]
        ),
        "upstream_executable_fixture_ids": frozenset(boundary["upstream_executable_fixture_ids"]),
        "downstream_scientific_execution_fixture_ids": frozenset(
            boundary["downstream_scientific_execution_fixture_ids"]
        ),
    }
    if len(set(boundary_copies.values())) != 1:
        raise CandidatePackError(f"declared boundary fixture sets disagree: {boundary_copies}")
    if require_active_references and _derived_pending_reference_ids(contract):
        raise CandidatePackError("pending reference blocks pack acceptance")

    if set(pack["lanes"]) != LANES:
        raise CandidatePackError("exact six-lane closure required")
    expected_fixtures = _rows_by_id(required["fixtures"]["exact_fixture_rows"], "fixture_id", "fixture")
    observed_fixtures = _rows_by_id(pack["required_fixtures"], "fixture_id", "fixture")
    if observed_fixtures != expected_fixtures:
        raise CandidatePackError("fixture rows must equal the exact upstream set")
    if set(observed_fixtures) != EXPECTED_FIXTURE_IDS:
        raise CandidatePackError("fixture ID closure differs from the independent fixture")

    profile = required["obligation_row_profile"]
    for lane_id, lane_contract in required["lanes"].items():
        lane = pack["lanes"][lane_id]
        if lane["lane_id"] != lane_id:
            raise CandidatePackError("lane key and lane_id must match")
        if set(lane["governing_reference_ids"]) != set(lane_contract["exact_governing_reference_ids"]) or len(
            lane["governing_reference_ids"]
        ) != len(lane_contract["exact_governing_reference_ids"]):
            raise CandidatePackError("lane reference relation differs from the exact upstream row")
        for reference_id in lane["governing_reference_ids"]:
            reference = observed_references.get(reference_id)
            if reference is None:
                raise CandidatePackError("dangling lane reference")
            if lane_id not in reference["allowed_lane_ids"]:
                raise CandidatePackError("foreign-valid reference is not allowed for lane")
        expected_obligations = _rows_by_id(
            [_expanded_obligation(row, profile) for row in lane_contract["required_obligations"]],
            "obligation_id",
            "obligation",
        )
        observed_obligations = _rows_by_id(lane["obligation_rows"], "obligation_id", "obligation")
        if observed_obligations != expected_obligations:
            raise CandidatePackError("obligation rows must equal the exact upstream lane set")
        if set(observed_obligations) != EXPECTED_OBLIGATION_IDS[lane_id]:
            raise CandidatePackError("obligation closure differs from the independent W5 fixture")
        if set(lane["fixture_ids"]) != set(lane_contract["exact_fixture_ids"]) or len(lane["fixture_ids"]) != len(
            lane_contract["exact_fixture_ids"]
        ):
            raise CandidatePackError("lane fixture relation differs from the exact upstream row")
        if not set(lane["fixture_ids"]) <= set(observed_fixtures):
            raise CandidatePackError("dangling lane fixture")
        for fixture_id in lane["fixture_ids"]:
            fixture_lane_id = observed_fixtures[fixture_id]["lane_id"]
            if fixture_lane_id not in {lane_id, "cross_lane"}:
                raise CandidatePackError("lane declares a fixture catalogued to a foreign lane")
    _validate_lane_enforcer_relation(pack, observed_references)

    authored_at = _parse_datetime(pack["currency"]["authored_at"])
    effective_at = _parse_datetime(pack["currency"]["effective_at"])
    expires_at = _parse_datetime(pack["currency"]["expires_at"])
    if not authored_at <= effective_at < expires_at:
        raise CandidatePackError("candidate currency time order is invalid")
    if expires_at <= as_of:
        raise CandidatePackError("candidate currency expired")


def _validate_proposed_pack(
    pack: dict,
    *,
    contract: dict | None = None,
    require_active_references: bool = False,
    registered_pack_ids: frozenset[str] = frozenset({ASSURANCE_PACK_ID}),
    as_of: datetime = AS_OF,
) -> None:
    """Validate a consumer candidate against contract bytes resolved internally from Git."""
    _validate_proposed_pack_with_authority(
        pack,
        contract=contract,
        require_active_references=require_active_references,
        registered_pack_ids=registered_pack_ids,
        as_of=as_of,
    )


def _validate_hypothetical_proposed_pack(
    pack: dict,
    *,
    contract: dict,
    fixture_contract_authority: _FixtureContractAuthority,
    require_active_references: bool = False,
    registered_pack_ids: frozenset[str] = frozenset({ASSURANCE_PACK_ID}),
    as_of: datetime = AS_OF,
) -> None:
    """Exercise hypothetical contract variants without widening the consumer entry point."""
    _require_issued_fixture_authority(fixture_contract_authority)
    _validate_proposed_pack_with_authority(
        pack,
        contract=contract,
        trusted_contract_resolver=fixture_contract_authority,
        require_active_references=require_active_references,
        registered_pack_ids=registered_pack_ids,
        as_of=as_of,
    )


def _pack_subject(raw_candidate_pack_bytes: bytes, *, expected_pack: dict | None = None) -> dict:
    pack = _parse_candidate_pack_bytes(raw_candidate_pack_bytes)
    if expected_pack is not None and pack != expected_pack:
        raise CandidatePackError("raw candidate bytes do not parse to the supplied candidate")
    return {
        "pack_id": pack["pack_id"],
        "assurance_pack_id": pack["assurance_pack_id"],
        "assurance_pack_revision": pack["assurance_pack_revision"],
        "canonical_repository_path": pack["canonical_repository_path"],
        "pack_git_blob": _git_blob_id(raw_candidate_pack_bytes),
        "pack_raw_sha256": hashlib.sha256(raw_candidate_pack_bytes).hexdigest(),
        "schema_id": pack["schema_reference"]["schema_id"],
        "schema_version": pack["schema_reference"]["schema_version"],
        "schema_repository_path": pack["schema_reference"]["repository_path"],
        "schema_git_blob": pack["schema_reference"]["git_blob"],
        "schema_canonical_sha256": pack["schema_reference"]["canonical_sha256"],
    }


def _rehash_record(record_store: dict[str, dict], hash_manifest: dict[str, str], record_id: str) -> None:
    hash_manifest[record_id] = _canonical_sha256(record_store[record_id])


def _actor_record(actor_id: str, canonical_name: str, *, actor_kind: str = "agent") -> dict:
    return {
        "record_type": "canonical_actor",
        "actor_id": actor_id,
        "actor_kind": actor_kind,
        "canonical_name": canonical_name,
        "status": "active",
    }


def _obligation_applicability_rows(contract: dict) -> list[dict]:
    return [
        {
            "lane_id": lane_id,
            "obligation_id": obligation["obligation_id"],
            "applicability": "required",
            "rationale": "required_by_accepted_tdl_private_pack_contract",
            "decision_author_actor_id": ACT_REQUIREMENT_AUTHOR,
            "confirming_actor_id": ACT_SCOPE_REVIEWER,
            "prospective_producer_actor_id": ACT_PRODUCER,
            "relationship_record_id": SCOPE_RELATIONSHIP_ID,
            "minimum_independence_grade": "I2",
            "decided_at": "2026-07-18T08:20:00Z",
        }
        for lane_id, lane in contract["required_pack_contract"]["lanes"].items()
        for obligation in lane["required_obligations"]
    ]


def _canonical_assurance_requirement(contract: dict, contract_subject: dict) -> dict:
    requirement = {
        "schema_id": "ars://assurance/assurance-requirement",
        "schema_version": "1.0.0",
        "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
        "revision": 1,
        "task_id": PRODUCER_TASK_ID,
        "task_revision": 1,
        "requested_risk": "R3",
        "w5_epistemic_risk_floor": "R3",
        "action_semantic_risk": "R3",
        "requirement_relationship_grade": "I2",
        "lanes": list(contract["required_pack_contract"]["six_lane_closure"]),
        "currency_hash": _canonical_sha256(
            {
                "contract_subject": contract_subject,
                "governing_sources": contract["source_authority"]["governing_sources"],
                "references": contract["required_pack_contract"]["references"]["exact_reference_rows"],
            }
        ),
    }
    requirement["content_hash"] = _canonical_sha256(requirement)
    return requirement


def _obligation_evidence_rows(contract: dict) -> list[dict]:
    return [
        {
            "lane_id": lane_id,
            "obligation_id": obligation["obligation_id"],
            "key_a_status": "passed",
            "key_a_evidence_ids": [obligation["evidence_output_id"]],
            "key_b_status": "passed",
            "key_b_evidence_ids": [obligation["review_question_id"]],
            "forbidden_state_or_claim": "absent",
        }
        for lane_id, lane in contract["required_pack_contract"]["lanes"].items()
        for obligation in lane["required_obligations"]
    ]


def _boundary_fixture_execution_rows() -> list[dict]:
    return [
        {
            "fixture_id": fixture_id,
            "execution_status": "executed",
            "expected_outcome": "blocked",
            "observed_outcome": "blocked",
            "key_a_status": "passed",
            "key_b_status": "passed",
        }
        for fixture_id in (
            "apf_tested_object_no_op",
            "apf_degenerate_fallback",
            "apf_claim_escalation",
        )
    ]


def _two_key_closure_sha256(review: dict) -> str:
    return _canonical_sha256(
        {
            "obligation_evidence_rows": review["obligation_evidence_rows"],
            "boundary_fixture_execution_rows": review["boundary_fixture_execution_rows"],
        }
    )


def _requirement_content_preimage(requirement: dict) -> dict:
    return {
        "assurance_requirement_id": requirement["assurance_requirement_id"],
        "revision": requirement["revision"],
        "subject_contract": requirement["subject_contract"],
        "canonical_requirement": requirement["canonical_requirement"],
        "prospective_producer_actor_id": requirement["prospective_producer_actor_id"],
        "obligation_applicability_rows": requirement["obligation_applicability_rows"],
    }


def _applicability_decision_preimage(requirement: dict, row: dict) -> dict:
    """Return the acyclic decision surface bound by an external N/A confirmation."""
    return {
        "assurance_requirement_id": requirement["assurance_requirement_id"],
        "revision": requirement["revision"],
        "subject_contract": requirement["subject_contract"],
        **{
            key: row[key]
            for key in (
                "lane_id",
                "obligation_id",
                "applicability",
                "rationale",
                "decision_author_actor_id",
                "confirming_actor_id",
                "prospective_producer_actor_id",
                "relationship_record_id",
                "minimum_independence_grade",
                "decided_at",
            )
        },
    }


def _install_applicability_confirmation(
    record_store: dict[str, dict],
    *,
    confirmation_id: str = APPLICABILITY_CONFIRMATION_ID,
    confirmed_at: str = "2026-07-18T08:25:00Z",
) -> dict:
    """Install a separately content-addressed independent confirmation for row zero."""
    requirement = record_store[REQUIREMENT_RECORD_ID]
    row = requirement["obligation_applicability_rows"][0]
    decision_preimage = _applicability_decision_preimage(requirement, row)
    confirmation = {
        "record_type": "obligation_applicability_confirmation",
        "confirmation_record_id": confirmation_id,
        **deepcopy(decision_preimage),
        "applicability_decision_sha256": _canonical_sha256(decision_preimage),
        "confirmation_state": "active",
        "confirmed_at": confirmed_at,
    }
    record_store[confirmation_id] = confirmation
    row["confirmation_record_id"] = confirmation_id
    row["confirmation_record_sha256"] = _canonical_sha256(confirmation)
    return confirmation


def _external_records(pack: dict, contract: dict) -> tuple[dict, bytes, dict[str, dict], dict[str, str]]:
    contract_subject = deepcopy(pack["upstream_contract_reference"])
    pack_schema_subject = deepcopy(pack["schema_reference"])
    authorship_record = {
        "record_type": "contract_schema_authorship",
        "authorship_record_id": CONTRACT_AUTHORSHIP_RECORD_ID,
        "contract_subject": deepcopy(contract_subject),
        "pack_schema_subject": deepcopy(pack_schema_subject),
        "author_actor_id": ACT_CONTRACT_AUTHOR,
        "authorship_state": "completed",
        "authored_at": "2026-07-18T07:10:00Z",
    }
    authorship_hash = _canonical_sha256(authorship_record)
    contract_review = {
        "record_type": "independent_contract_review",
        "review_record_id": CONTRACT_REVIEW_RECORD_ID,
        "contract_subject": deepcopy(contract_subject),
        "pack_schema_subject": deepcopy(pack_schema_subject),
        "authorship_record_id": CONTRACT_AUTHORSHIP_RECORD_ID,
        "authorship_record_sha256": authorship_hash,
        "reviewer_actor_id": ACT_CONTRACT_REVIEWER,
        "author_actor_id": ACT_CONTRACT_AUTHOR,
        "relationship_record_id": CONTRACT_REVIEW_RELATIONSHIP_ID,
        "minimum_independence_grade": "I2",
        "operator_provenance": _review_operator_provenance(
            producer_actor_id=ACT_CONTRACT_AUTHOR,
            reviewer_actor_id=ACT_CONTRACT_REVIEWER,
            review_task_id=CONTRACT_REVIEW_TASK_ID,
            review_session_id=CONTRACT_REVIEW_SESSION_ID,
        ),
        "verdict": "pass",
        "review_state": "completed",
        "reviewed_at": "2026-07-18T07:30:00Z",
    }
    schema_review = {
        "record_type": "independent_schema_review",
        "review_record_id": SCHEMA_REVIEW_RECORD_ID,
        "pack_schema_subject": deepcopy(pack_schema_subject),
        "contract_subject": deepcopy(contract_subject),
        "authorship_record_id": CONTRACT_AUTHORSHIP_RECORD_ID,
        "authorship_record_sha256": authorship_hash,
        "reviewer_actor_id": ACT_SCHEMA_REVIEWER,
        "author_actor_id": ACT_CONTRACT_AUTHOR,
        "relationship_record_id": SCHEMA_REVIEW_RELATIONSHIP_ID,
        "minimum_independence_grade": "I2",
        "operator_provenance": _review_operator_provenance(
            producer_actor_id=ACT_CONTRACT_AUTHOR,
            reviewer_actor_id=ACT_SCHEMA_REVIEWER,
            review_task_id=SCHEMA_REVIEW_TASK_ID,
            review_session_id=SCHEMA_REVIEW_SESSION_ID,
        ),
        "verdict": "pass",
        "review_state": "completed",
        "reviewed_at": "2026-07-18T07:35:00Z",
    }
    contract_schema_acceptance = {
        "record_type": "stephen_contract_schema_acceptance",
        "owner_decision_id": CONTRACT_SCHEMA_ACCEPTANCE_ID,
        "contract_subject": deepcopy(contract_subject),
        "pack_schema_subject": deepcopy(pack_schema_subject),
        "authorship_record_id": CONTRACT_AUTHORSHIP_RECORD_ID,
        "authorship_record_sha256": authorship_hash,
        "contract_review_record_id": CONTRACT_REVIEW_RECORD_ID,
        "contract_review_record_sha256": _canonical_sha256(contract_review),
        "schema_review_record_id": SCHEMA_REVIEW_RECORD_ID,
        "schema_review_record_sha256": _canonical_sha256(schema_review),
        "acceptor_actor_id": ACT_OWNER,
        "outcome": "accepted",
        "decision_state": "active",
        "decided_at": "2026-07-18T08:00:00Z",
    }
    applicability_rows = _obligation_applicability_rows(contract)
    requirement_record = {
        "record_type": "accepted_assurance_requirement",
        "acceptance_record_id": REQUIREMENT_RECORD_ID,
        "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
        "revision": 1,
        "subject_contract": deepcopy(contract_subject),
        "canonical_requirement": _canonical_assurance_requirement(contract, contract_subject),
        "obligation_applicability_rows": applicability_rows,
        "requirement_author_actor_id": ACT_REQUIREMENT_AUTHOR,
        "scope_reviewer_actor_id": ACT_SCOPE_REVIEWER,
        "acceptor_actor_id": ACT_OWNER,
        "prospective_producer_actor_id": ACT_PRODUCER,
        "minimum_independence_grade": "I2",
        "scope_relationship_record_id": SCOPE_RELATIONSHIP_ID,
        "outcome": "accepted",
        "acceptance_state": "active",
        "accepted_at": "2026-07-18T08:30:00Z",
    }
    requirement_record["requirement_subject"] = {
        "schema_id": "ars://assurance/assurance-requirement",
        "schema_version": "1.0.0",
        "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
        "revision": 1,
        "content_surface": "canonical_json_utf8",
        "canonical_sha256": _canonical_sha256(_requirement_content_preimage(requirement_record)),
        "canonical_requirement_sha256": _canonical_sha256(requirement_record["canonical_requirement"]),
    }
    requirement_hash = _canonical_sha256(requirement_record)
    pack["assurance_requirement_reference"]["acceptance_record_sha256"] = requirement_hash
    raw_candidate_pack_bytes = _raw_pack_bytes(pack)
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    scope_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": SCOPE_RELATIONSHIP_ID,
        "relationship_context": "requirement_scope_review",
        "subject_actor_id": ACT_SCOPE_REVIEWER,
        "object_actor_id": ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T08:15:00Z",
        "expires_at": "2027-07-18T08:15:00Z",
    }
    review_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": REVIEW_RELATIONSHIP_ID,
        "relationship_context": "pack_scientific_review",
        "subject_actor_id": ACT_SCIENTIFIC_REVIEWER,
        "object_actor_id": ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T09:20:00Z",
        "expires_at": "2027-07-18T09:30:00Z",
    }
    contract_review_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": CONTRACT_REVIEW_RELATIONSHIP_ID,
        "relationship_context": "contract_review",
        "subject_actor_id": ACT_CONTRACT_REVIEWER,
        "object_actor_id": ACT_CONTRACT_AUTHOR,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T07:00:00Z",
        "expires_at": "2027-07-18T07:00:00Z",
    }
    schema_review_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": SCHEMA_REVIEW_RELATIONSHIP_ID,
        "relationship_context": "schema_review",
        "subject_actor_id": ACT_SCHEMA_REVIEWER,
        "object_actor_id": ACT_CONTRACT_AUTHOR,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T07:00:00Z",
        "expires_at": "2027-07-18T07:00:00Z",
    }
    review_record = {
        "record_type": "independent_pack_review",
        "review_record_id": REVIEW_RECORD_ID,
        "subject": deepcopy(subject),
        "reviewer_actor_id": ACT_SCIENTIFIC_REVIEWER,
        "producer_actor_id": ACT_PRODUCER,
        "relationship_record_id": REVIEW_RELATIONSHIP_ID,
        "minimum_independence_grade": "I2",
        "operator_provenance": _review_operator_provenance(
            producer_actor_id=ACT_PRODUCER,
            reviewer_actor_id=ACT_SCIENTIFIC_REVIEWER,
            review_task_id=REVIEW_TASK_ID,
            review_session_id=REVIEW_SESSION_ID,
            producer_task_id=PRODUCER_TASK_ID,
            producer_session_id=PRODUCER_SESSION_ID,
        ),
        "obligation_evidence_rows": _obligation_evidence_rows(contract),
        "boundary_fixture_execution_rows": _boundary_fixture_execution_rows(),
        "verdict": "pass",
        "review_state": "completed",
        "reviewed_at": "2026-07-18T10:00:00Z",
    }
    review_record["two_key_closure_sha256"] = _two_key_closure_sha256(review_record)
    review_hash = _canonical_sha256(review_record)
    owner_grant = {
        "record_type": "active_authority_grant",
        "authority_grant_id": OWNER_GRANT_ID,
        "actor_id": ACT_OWNER,
        "authority_class": "stephen_reserved_owner_acceptance",
        "subject_assurance_pack_id": ASSURANCE_PACK_ID,
        "grant_state": "active",
        "effective_at": "2026-07-18T07:00:00Z",
        "expires_at": "2027-07-18T07:00:00Z",
        "revoked": False,
    }
    owner_decision = {
        "record_type": "stephen_owner_acceptance",
        "owner_decision_id": OWNER_DECISION_ID,
        "subject": deepcopy(subject),
        "review_record_id": REVIEW_RECORD_ID,
        "review_record_sha256": review_hash,
        "acceptor_actor_id": ACT_OWNER,
        "authority_grant_id": OWNER_GRANT_ID,
        "two_key_closure_sha256": review_record["two_key_closure_sha256"],
        "outcome": "accepted",
        "decision_state": "active",
        "decided_at": "2026-07-18T11:00:00Z",
    }
    pack_registry = {
        "record_type": "registered_pack_object",
        "assurance_pack_id": ASSURANCE_PACK_ID,
        "id_kind": "assurance_pack",
        "revision": 1,
        "canonical_repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "registration_state": "active",
        "registered_at": "2026-07-18T08:45:00Z",
    }
    record_store = {
        ACT_CONTRACT_AUTHOR: _actor_record(ACT_CONTRACT_AUTHOR, "contract-author-agent"),
        ACT_PRODUCER: _actor_record(ACT_PRODUCER, "future-pack-producer-agent"),
        ACT_REQUIREMENT_AUTHOR: _actor_record(ACT_REQUIREMENT_AUTHOR, "requirement-author-agent"),
        ACT_SCOPE_REVIEWER: _actor_record(ACT_SCOPE_REVIEWER, "requirement-scope-reviewer-agent"),
        ACT_SCIENTIFIC_REVIEWER: _actor_record(ACT_SCIENTIFIC_REVIEWER, "pack-scientific-reviewer-agent"),
        ACT_OWNER: _actor_record(ACT_OWNER, "Stephen", actor_kind="human"),
        ACT_CONTRACT_REVIEWER: _actor_record(ACT_CONTRACT_REVIEWER, "contract-reviewer-agent"),
        ACT_SCHEMA_REVIEWER: _actor_record(ACT_SCHEMA_REVIEWER, "schema-reviewer-agent"),
        CONTRACT_AUTHORSHIP_RECORD_ID: authorship_record,
        CONTRACT_REVIEW_RECORD_ID: contract_review,
        SCHEMA_REVIEW_RECORD_ID: schema_review,
        CONTRACT_SCHEMA_ACCEPTANCE_ID: contract_schema_acceptance,
        REQUIREMENT_RECORD_ID: requirement_record,
        SCOPE_RELATIONSHIP_ID: scope_relationship,
        REVIEW_RELATIONSHIP_ID: review_relationship,
        CONTRACT_REVIEW_RELATIONSHIP_ID: contract_review_relationship,
        SCHEMA_REVIEW_RELATIONSHIP_ID: schema_review_relationship,
        REVIEW_RECORD_ID: review_record,
        OWNER_GRANT_ID: owner_grant,
        OWNER_DECISION_ID: owner_decision,
        ASSURANCE_PACK_ID: pack_registry,
    }
    hash_manifest = {record_id: _canonical_sha256(record) for record_id, record in record_store.items()}
    return pack, raw_candidate_pack_bytes, record_store, hash_manifest


def _refresh_acceptance_chain(pack: dict, record_store: dict[str, dict], hash_manifest: dict[str, str]) -> bytes:
    requirement = record_store[REQUIREMENT_RECORD_ID]
    requirement["requirement_subject"]["canonical_sha256"] = _canonical_sha256(
        _requirement_content_preimage(requirement)
    )
    _rehash_record(record_store, hash_manifest, REQUIREMENT_RECORD_ID)
    pack["assurance_requirement_reference"]["acceptance_record_sha256"] = hash_manifest[REQUIREMENT_RECORD_ID]
    raw_candidate_pack_bytes = _raw_pack_bytes(pack)
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    record_store[REVIEW_RECORD_ID]["subject"] = deepcopy(subject)
    record_store[REVIEW_RECORD_ID]["two_key_closure_sha256"] = _two_key_closure_sha256(record_store[REVIEW_RECORD_ID])
    _rehash_record(record_store, hash_manifest, REVIEW_RECORD_ID)
    record_store[OWNER_DECISION_ID]["subject"] = deepcopy(subject)
    record_store[OWNER_DECISION_ID]["review_record_sha256"] = hash_manifest[REVIEW_RECORD_ID]
    record_store[OWNER_DECISION_ID]["two_key_closure_sha256"] = record_store[REVIEW_RECORD_ID]["two_key_closure_sha256"]
    _rehash_record(record_store, hash_manifest, OWNER_DECISION_ID)
    return raw_candidate_pack_bytes


def _coordinate_all_external_hashes(pack: dict, record_store: dict[str, dict]) -> tuple[bytes, dict[str, str]]:
    hash_manifest = {record_id: _canonical_sha256(record) for record_id, record in record_store.items()}
    raw_candidate_pack_bytes = _refresh_acceptance_chain(pack, record_store, hash_manifest)
    return raw_candidate_pack_bytes, hash_manifest


def _eligible_acceptance_fixture(
    contract: dict | None = None,
) -> tuple[dict, ContractAuthorityResolver, dict, bytes, dict[str, dict], dict[str, str]]:
    """Build an acceptance fixture, optionally over a caller-narrowed contract.

    `contract` lets a test exercise a configuration the repository contract does not currently
    declare — e.g. an operator model admitting only one session family — so that a value which is
    schema-valid but contract-disallowed can reach the validator. It is still schema-validated
    here and still frozen behind the fixture authority seam.
    """
    contract = _eligible_contract() if contract is None else deepcopy(contract)
    _schema_registry().validate(CONTRACT_SCHEMA_ID, contract)
    _validate_pending_reference_relation(contract)
    contract_resolver = _fixture_contract_authority(contract)
    _, _, contract_subject = _resolve_contract_authority(contract_resolver)
    pack = _proposed_pack(contract, contract_subject=contract_subject)
    pack, raw_candidate_pack_bytes, record_store, hash_manifest = _external_records(pack, contract)
    return contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest


def _resolved_record(
    contract: dict,
    record_store: dict[str, dict],
    hash_manifest: dict[str, str],
    record_id: str,
    record_class: str,
) -> dict:
    if record_id not in record_store or record_id not in hash_manifest:
        raise CandidatePackError(f"missing external record: {record_id}")
    record = record_store[record_id]
    if _canonical_sha256(record) != hash_manifest[record_id]:
        raise CandidatePackError(f"external record hash mismatch: {record_id}")
    _validate_external_record(contract, record, record_class)
    identity_fields = {
        "canonical_actor": "actor_id",
        "producer_relationship_evidence": "relationship_record_id",
        "contract_schema_authorship": "authorship_record_id",
        "independent_contract_review": "review_record_id",
        "independent_schema_review": "review_record_id",
        "stephen_contract_schema_acceptance": "owner_decision_id",
        "accepted_assurance_requirement": "acceptance_record_id",
        "obligation_applicability_confirmation": "confirmation_record_id",
        "independent_pack_review": "review_record_id",
        "stephen_owner_acceptance": "owner_decision_id",
        "active_authority_grant": "authority_grant_id",
        "registered_pack_object": "assurance_pack_id",
    }
    if record[identity_fields[record_class]] != record_id:
        raise CandidatePackError(f"external record key/body identity mismatch: {record_id}")
    return record


def _validate_external_acceptance_with_authority(
    pack: dict,
    *,
    raw_candidate_pack_bytes: bytes,
    contract: dict,
    trusted_contract_resolver: ContractAuthorityResolver | None,
    authority_resolver: _FixtureRecordAuthority,
    review_record_id: str = REVIEW_RECORD_ID,
    owner_decision_id: str = OWNER_DECISION_ID,
    as_of: datetime = AS_OF,
) -> None:
    load_snapshot = _resolve_authority_phase(authority_resolver, "load", contract)
    authority_root = load_snapshot.authority_root_sha256
    record_store = load_snapshot.record_store
    hash_manifest = load_snapshot.record_hashes
    parsed_pack = _parse_candidate_pack_bytes(raw_candidate_pack_bytes)
    if parsed_pack != pack:
        raise CandidatePackError("raw candidate bytes do not parse to the supplied candidate")
    _validate_proposed_pack_with_authority(
        parsed_pack,
        contract=contract,
        trusted_contract_resolver=trusted_contract_resolver,
        require_active_references=True,
        as_of=as_of,
    )
    _, trusted_contract, accepted_contract_subject = _resolve_contract_authority(trusted_contract_resolver)
    if trusted_contract != contract:
        raise CandidatePackError("supplied contract differs from trusted Git contract authority")
    accepted_pack_schema_subject = _resolve_external_schema_reference()
    authorship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        CONTRACT_AUTHORSHIP_RECORD_ID,
        "contract_schema_authorship",
    )
    contract_review = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        CONTRACT_REVIEW_RECORD_ID,
        "independent_contract_review",
    )
    schema_review = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        SCHEMA_REVIEW_RECORD_ID,
        "independent_schema_review",
    )
    contract_schema_acceptance = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        CONTRACT_SCHEMA_ACCEPTANCE_ID,
        "stephen_contract_schema_acceptance",
    )
    lifecycle_records = (authorship, contract_review, schema_review, contract_schema_acceptance)
    if any(record["contract_subject"] != accepted_contract_subject for record in lifecycle_records):
        raise CandidatePackError("contract lifecycle does not bind the accepted contract subject")
    if any(record["pack_schema_subject"] != accepted_pack_schema_subject for record in lifecycle_records):
        raise CandidatePackError("contract lifecycle does not bind the accepted pack schema subject")
    if (
        contract_review["authorship_record_id"] != CONTRACT_AUTHORSHIP_RECORD_ID
        or contract_review["authorship_record_sha256"] != hash_manifest[CONTRACT_AUTHORSHIP_RECORD_ID]
        or schema_review["authorship_record_id"] != CONTRACT_AUTHORSHIP_RECORD_ID
        or schema_review["authorship_record_sha256"] != hash_manifest[CONTRACT_AUTHORSHIP_RECORD_ID]
    ):
        raise CandidatePackError("contract/schema review does not bind exact authorship")
    contract_review_provenance = _validate_review_operator_provenance(
        contract,
        contract_review,
        producer_actor_id=authorship["author_actor_id"],
        reviewer_actor_id=contract_review["reviewer_actor_id"],
        label="contract",
    )
    schema_review_provenance = _validate_review_operator_provenance(
        contract,
        schema_review,
        producer_actor_id=authorship["author_actor_id"],
        reviewer_actor_id=schema_review["reviewer_actor_id"],
        label="schema",
    )
    _checked_review_provenance_record_types = {
        contract_review["record_type"],
        schema_review["record_type"],
    }
    if (
        contract_schema_acceptance["authorship_record_id"] != CONTRACT_AUTHORSHIP_RECORD_ID
        or contract_schema_acceptance["authorship_record_sha256"] != hash_manifest[CONTRACT_AUTHORSHIP_RECORD_ID]
        or contract_schema_acceptance["contract_review_record_id"] != CONTRACT_REVIEW_RECORD_ID
        or contract_schema_acceptance["contract_review_record_sha256"] != hash_manifest[CONTRACT_REVIEW_RECORD_ID]
        or contract_schema_acceptance["schema_review_record_id"] != SCHEMA_REVIEW_RECORD_ID
        or contract_schema_acceptance["schema_review_record_sha256"] != hash_manifest[SCHEMA_REVIEW_RECORD_ID]
    ):
        raise CandidatePackError("Stephen contract/schema acceptance does not bind exact lifecycle records")
    if (
        authorship["author_actor_id"] != contract_review["author_actor_id"]
        or authorship["author_actor_id"] != schema_review["author_actor_id"]
        or len(
            {
                authorship["author_actor_id"],
                contract_review["reviewer_actor_id"],
                schema_review["reviewer_actor_id"],
                contract_schema_acceptance["acceptor_actor_id"],
                pack["producer_actor_id"],
            }
        )
        != 5
    ):
        raise CandidatePackError("contract authorship, reviews, owner acceptance, and production must be distinct")
    requirement_id = pack["assurance_requirement_reference"]["acceptance_record_id"]
    requirement = _resolved_record(
        contract, record_store, hash_manifest, requirement_id, "accepted_assurance_requirement"
    )
    if hash_manifest[requirement_id] != pack["assurance_requirement_reference"]["acceptance_record_sha256"]:
        raise CandidatePackError("candidate requirement reference does not match external record")
    if requirement["subject_contract"] != accepted_contract_subject:
        raise CandidatePackError("assurance requirement binds a different upstream contract")
    if (
        requirement["assurance_requirement_id"] != pack["assurance_requirement_reference"]["assurance_requirement_id"]
        or requirement["revision"] != pack["assurance_requirement_reference"]["revision"]
    ):
        raise CandidatePackError("assurance requirement identity mismatch")
    if requirement["prospective_producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("accepted requirement names a different producer")
    requirement_subject = requirement["requirement_subject"]
    canonical_requirement = requirement["canonical_requirement"]
    canonical_preimage = {key: value for key, value in canonical_requirement.items() if key != "content_hash"}
    if (
        requirement_subject["assurance_requirement_id"] != requirement["assurance_requirement_id"]
        or requirement_subject["revision"] != requirement["revision"]
        or requirement_subject["canonical_sha256"] != _canonical_sha256(_requirement_content_preimage(requirement))
        or requirement_subject["canonical_requirement_sha256"] != _canonical_sha256(canonical_requirement)
        or canonical_requirement["content_hash"] != _canonical_sha256(canonical_preimage)
        or canonical_requirement["assurance_requirement_id"] != requirement["assurance_requirement_id"]
        or canonical_requirement["revision"] != requirement["revision"]
        or canonical_requirement["requested_risk"] != "R3"
        or canonical_requirement["w5_epistemic_risk_floor"] != "R3"
        or canonical_requirement["action_semantic_risk"] != "R3"
        or canonical_requirement["requirement_relationship_grade"] != requirement["minimum_independence_grade"]
        or canonical_requirement["lanes"] != contract["required_pack_contract"]["six_lane_closure"]
        or canonical_requirement["currency_hash"]
        != _canonical_assurance_requirement(contract, accepted_contract_subject)["currency_hash"]
    ):
        raise CandidatePackError("canonical AssuranceRequirement bytes or identity mismatch")
    expected_applicability = {
        (lane_id, obligation["obligation_id"])
        for lane_id, lane in contract["required_pack_contract"]["lanes"].items()
        for obligation in lane["required_obligations"]
    }
    applicability_rows = requirement["obligation_applicability_rows"]
    observed_applicability = {(row["lane_id"], row["obligation_id"]) for row in applicability_rows}
    if len(observed_applicability) != len(applicability_rows) or observed_applicability != expected_applicability:
        raise CandidatePackError("accepted requirement applicability closure differs")
    scope_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        requirement["scope_relationship_record_id"],
        "producer_relationship_evidence",
    )
    requirement_accepted_at = _parse_datetime(requirement["accepted_at"])
    relationship_effective_at = _parse_datetime(scope_relationship["effective_at"])
    relationship_expires_at = _parse_datetime(scope_relationship["expires_at"])
    for row in applicability_rows:
        if (
            row["prospective_producer_actor_id"] != pack["producer_actor_id"]
            or row["decision_author_actor_id"] != requirement["requirement_author_actor_id"]
            or row["confirming_actor_id"] != requirement["scope_reviewer_actor_id"]
            or row["relationship_record_id"] != requirement["scope_relationship_record_id"]
            or row["minimum_independence_grade"] != requirement["minimum_independence_grade"]
        ):
            raise CandidatePackError("accepted requirement applicability authority is unbound")
        row_decided_at = _parse_datetime(row["decided_at"])
        if not (
            relationship_effective_at <= row_decided_at <= requirement_accepted_at <= as_of < relationship_expires_at
        ):
            raise CandidatePackError("applicability decision time is outside relationship or acceptance bounds")
        if row["applicability"] == "not_applicable":
            confirmation_id = row["confirmation_record_id"]
            confirmation = _resolved_record(
                contract,
                record_store,
                hash_manifest,
                confirmation_id,
                "obligation_applicability_confirmation",
            )
            if row["confirmation_record_sha256"] != hash_manifest[confirmation_id]:
                raise CandidatePackError("applicability confirmation hash does not bind the external record")
            decision_preimage = _applicability_decision_preimage(requirement, row)
            if confirmation["applicability_decision_sha256"] != _canonical_sha256(decision_preimage) or any(
                confirmation[key] != value for key, value in decision_preimage.items()
            ):
                raise CandidatePackError("applicability confirmation does not bind the exact decision")
            confirmed_at = _parse_datetime(confirmation["confirmed_at"])
            if not row_decided_at <= confirmed_at <= requirement_accepted_at:
                raise CandidatePackError("applicability confirmation time is outside decision or acceptance bounds")
            if confirmation["confirming_actor_id"] == pack["producer_actor_id"]:
                raise CandidatePackError("applicability confirmation is not producer-independent")
    review = _resolved_record(contract, record_store, hash_manifest, review_record_id, "independent_pack_review")
    acceptance_snapshot = _resolve_authority_phase(
        authority_resolver,
        "acceptance",
        contract,
        expected_root=authority_root,
    )
    if acceptance_snapshot.record_store != record_store or acceptance_snapshot.record_hashes != hash_manifest:
        raise CandidatePackError("authority records changed during acceptance revalidation")
    review_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        review["relationship_record_id"],
        "producer_relationship_evidence",
    )
    contract_review_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        contract_review["relationship_record_id"],
        "producer_relationship_evidence",
    )
    schema_review_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        schema_review["relationship_record_id"],
        "producer_relationship_evidence",
    )
    owner = _resolved_record(contract, record_store, hash_manifest, owner_decision_id, "stephen_owner_acceptance")
    grant = _resolved_record(
        contract, record_store, hash_manifest, owner["authority_grant_id"], "active_authority_grant"
    )
    registered_object = _resolved_record(
        contract, record_store, hash_manifest, pack["assurance_pack_id"], "registered_pack_object"
    )
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    if review["subject"] != subject:
        raise CandidatePackError("independent review subject does not match loader-computed pack subject")
    if owner["subject"] != subject:
        raise CandidatePackError("owner decision subject does not match loader-computed pack subject")
    if (
        owner["review_record_id"] != review_record_id
        or owner["review_record_sha256"] != hash_manifest[review_record_id]
    ):
        raise CandidatePackError("owner decision does not bind the exact independent review")
    evidence_rows: dict[tuple[str, str], dict] = {}
    for row in review["obligation_evidence_rows"]:
        row_key = (row["lane_id"], row["obligation_id"])
        if row_key in evidence_rows:
            raise CandidatePackError(f"duplicate two-key evidence row: {row_key}")
        evidence_rows[row_key] = row
    # Per-row status is owned by the external-record schema, not here: `obligationEvidenceRow`
    # pins key_a_status/key_b_status to const "passed" and forbidden_state_or_claim to const
    # "absent", and `nonEmptyStrings` gives both evidence-id lists minItems 1. Every row is
    # schema-validated by `_resolved_record` before reaching this check, so branches on those
    # fields could never fire — and an unreachable branch can never be given a watched negative.
    # The schema-level negative control lives in
    # tests/research_system/contracts/test_tdl_private_pack_candidate.py
    # ::test_two_key_status_fields_are_owned_by_the_external_record_schema.
    # What remains here is what the schema cannot express: the exact key set and its count.
    if set(evidence_rows) != expected_applicability or len(evidence_rows) != 69:
        raise CandidatePackError("two-key evidence does not close every required obligation")
    fixture_rows = _rows_by_id(
        review["boundary_fixture_execution_rows"],
        "fixture_id",
        "boundary fixture evidence",
    )
    # As above: `boundaryFixtureExecutionRow` pins execution_status, expected_outcome,
    # observed_outcome, and both key statuses as consts, so only the fixture-id set is
    # checkable here. Derive that set from the contract's own declaration rather than
    # restating it: this was the third copy the boundary-set agreement check above exists
    # to protect, and a literal here would be the one copy nothing compares.
    declared_boundary_fixture_ids = contract["required_pack_contract"]["external_acceptance_evidence"][
        "required_executed_boundary_fixture_ids"
    ]
    if set(fixture_rows) != set(declared_boundary_fixture_ids):
        raise CandidatePackError("two-key evidence lacks executed boundary fixtures")
    expected_two_key_root = _two_key_closure_sha256(review)
    if (
        review["two_key_closure_sha256"] != expected_two_key_root
        or owner["two_key_closure_sha256"] != expected_two_key_root
    ):
        raise CandidatePackError("owner acceptance does not bind exact two-key evidence")
    provenance = _validate_review_operator_provenance(
        contract,
        review,
        producer_actor_id=pack["producer_actor_id"],
        reviewer_actor_id=review["reviewer_actor_id"],
        label="pack",
    )
    if canonical_requirement["task_id"] != provenance["producer_task_id"]:
        raise CandidatePackError("pack review task provenance does not prove a separate fresh context")
    if (
        len(
            {provenance["handoff_id"], contract_review_provenance["handoff_id"], schema_review_provenance["handoff_id"]}
        )
        != 1
    ):
        raise CandidatePackError("review provenance records do not share one stable handoff identifier")
    # Close review_provenance_partial_application: prohibited against the contract's own declared
    # set. Without this the declared list merely describes the call sites that happen to exist —
    # adding a fourth review record type, or a fourth entry here, would produce no failure. The
    # declaration has to be what the check reads, or it is prose beside code.
    checked_review_provenance_record_types = _checked_review_provenance_record_types | {review["record_type"]}
    evidence = contract["required_pack_contract"]["external_acceptance_evidence"]
    declared_review_provenance_record_types = set(evidence["review_provenance_required_record_types"])
    if evidence["review_provenance_partial_application"] != "prohibited":
        raise CandidatePackError("review provenance partial application must be prohibited")
    if checked_review_provenance_record_types != declared_review_provenance_record_types:
        raise CandidatePackError(
            "review provenance was not applied to every declared record type: "
            f"unchecked={sorted(declared_review_provenance_record_types - checked_review_provenance_record_types)}"
        )
    if review["verdict"] != "pass" or owner["outcome"] != "accepted":
        raise CandidatePackError("external review and owner acceptance are both required")
    if review["producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("independent review names a different producer")
    if requirement["minimum_independence_grade"] not in {"I2", "I3"}:
        raise CandidatePackError("requirement scope review is below I2")
    if review["minimum_independence_grade"] not in {"I2", "I3"}:
        raise CandidatePackError("pack review is below I2")
    if (
        scope_relationship["relationship_context"] != "requirement_scope_review"
        or scope_relationship["subject_actor_id"] != requirement["scope_reviewer_actor_id"]
        or scope_relationship["object_actor_id"] != pack["producer_actor_id"]
        or scope_relationship["grade"] != requirement["minimum_independence_grade"]
    ):
        raise CandidatePackError("scope relationship does not bind reviewer and producer")
    if (
        review_relationship["relationship_context"] != "pack_scientific_review"
        or review_relationship["subject_actor_id"] != review["reviewer_actor_id"]
        or review_relationship["object_actor_id"] != pack["producer_actor_id"]
    ):
        raise CandidatePackError("review relationship does not bind reviewer and producer")
    if review_relationship["grade"] != review["minimum_independence_grade"]:
        raise CandidatePackError("review relationship grade mismatch")
    for lifecycle_review, relationship, context in (
        (contract_review, contract_review_relationship, "contract_review"),
        (schema_review, schema_review_relationship, "schema_review"),
    ):
        if (
            relationship["relationship_context"] != context
            or relationship["subject_actor_id"] != lifecycle_review["reviewer_actor_id"]
            or relationship["object_actor_id"] != lifecycle_review["author_actor_id"]
            or relationship["grade"] != lifecycle_review["minimum_independence_grade"]
        ):
            raise CandidatePackError("contract/schema review relationship is unbound")
    actor_ids = {
        authorship["author_actor_id"],
        requirement["requirement_author_actor_id"],
        requirement["scope_reviewer_actor_id"],
        pack["producer_actor_id"],
        review["reviewer_actor_id"],
        owner["acceptor_actor_id"],
    }
    if len(actor_ids) != 6:
        raise CandidatePackError("authorship, production, review, and acceptance must be distinct")
    if requirement["acceptor_actor_id"] != owner["acceptor_actor_id"]:
        raise CandidatePackError("accepted requirement lacks the canonical Stephen acceptor")
    if contract_schema_acceptance["acceptor_actor_id"] != owner["acceptor_actor_id"]:
        raise CandidatePackError("contract/schema acceptance lacks the canonical Stephen acceptor")
    if requirement["acceptor_actor_id"] == pack["producer_actor_id"]:
        raise CandidatePackError("requirement acceptor must be independent of producer")
    for actor_id in actor_ids:
        _resolved_record(contract, record_store, hash_manifest, actor_id, "canonical_actor")
    for actor_id in (ACT_CONTRACT_REVIEWER, ACT_SCHEMA_REVIEWER):
        _resolved_record(contract, record_store, hash_manifest, actor_id, "canonical_actor")
    owner_actor = _resolved_record(contract, record_store, hash_manifest, owner["acceptor_actor_id"], "canonical_actor")
    if owner_actor["actor_kind"] != "human" or owner_actor["canonical_name"] != "Stephen":
        raise CandidatePackError("owner acceptance lacks the canonical Stephen actor")
    if (
        grant["actor_id"] != owner["acceptor_actor_id"]
        or grant["subject_assurance_pack_id"] != pack["assurance_pack_id"]
    ):
        raise CandidatePackError("owner acceptance lacks the canonical Stephen authority grant")
    if (
        registered_object["assurance_pack_id"] != pack["assurance_pack_id"]
        or registered_object["revision"] != pack["assurance_pack_revision"]
        or registered_object["canonical_repository_path"] != pack["canonical_repository_path"]
    ):
        raise CandidatePackError("assurance pack object registration mismatch")
    # Bind the remaining declared governed sets to the checks they name. Each of these keys was
    # previously read by nothing: the hardcoded checks nearby happened to agree with them, so the
    # declarations described the code instead of governing it, and an edit to either side would
    # have passed silently. The hardcoded checks are retained — these are additional, not
    # replacements.
    role_actor_ids = {
        "contract_author": authorship["author_actor_id"],
        "future_pack_producer": pack["producer_actor_id"],
        "contract_reviewer": contract_review["reviewer_actor_id"],
        "schema_reviewer": schema_review["reviewer_actor_id"],
        "owner_acceptor": owner["acceptor_actor_id"],
        "requirement_author": requirement["requirement_author_actor_id"],
        "requirement_scope_reviewer": requirement["scope_reviewer_actor_id"],
        "requirement_acceptor": requirement["acceptor_actor_id"],
        "pack_scientific_reviewer": review["reviewer_actor_id"],
    }
    for left, right in evidence["required_distinct_pairs"]:
        if left not in role_actor_ids or right not in role_actor_ids:
            raise CandidatePackError(f"required distinct pair names an unresolvable role: {left}/{right}")
        if role_actor_ids[left] == role_actor_ids[right]:
            raise CandidatePackError(f"required distinct pair is not distinct: {left}/{right}")
    contract_authored_at = _parse_datetime(authorship["authored_at"])
    contract_reviewed_at = _parse_datetime(contract_review["reviewed_at"])
    schema_reviewed_at = _parse_datetime(schema_review["reviewed_at"])
    contract_accepted_at = _parse_datetime(contract_schema_acceptance["decided_at"])
    registered_at = _parse_datetime(registered_object["registered_at"])
    authored_at = _parse_datetime(pack["currency"]["authored_at"])
    effective_at = _parse_datetime(pack["currency"]["effective_at"])
    reviewed_at = _parse_datetime(review["reviewed_at"])
    decided_at = _parse_datetime(owner["decided_at"])
    if not (
        contract_authored_at
        < min(contract_reviewed_at, schema_reviewed_at)
        <= max(contract_reviewed_at, schema_reviewed_at)
        < contract_accepted_at
        < requirement_accepted_at
        < authored_at
        < reviewed_at
        < decided_at
        <= as_of
    ):
        raise CandidatePackError(
            "temporal order must bind contract/schema lifecycle before requirement and pack acceptance"
        )
    if not requirement_accepted_at < registered_at <= authored_at <= effective_at < reviewed_at:
        raise CandidatePackError("pack registration and candidate effective-time order is invalid")
    stage_times = {
        "requirement_accepted": requirement_accepted_at,
        "candidate_authored": authored_at,
        "independent_reviewed": reviewed_at,
        "owner_accepted": decided_at,
    }
    declared_order = evidence["required_temporal_order"]
    if any(stage not in stage_times for stage in declared_order):
        raise CandidatePackError("required temporal order names an unresolvable lifecycle stage")
    ordered_times = [stage_times[stage] for stage in declared_order]
    if ordered_times != sorted(ordered_times) or len(set(ordered_times)) != len(ordered_times):
        raise CandidatePackError(f"declared temporal order is not satisfied: {declared_order}")
    for relationship, action_time in (
        (contract_review_relationship, contract_reviewed_at),
        (schema_review_relationship, schema_reviewed_at),
        (scope_relationship, requirement_accepted_at),
        (review_relationship, reviewed_at),
    ):
        if (
            not _parse_datetime(relationship["effective_at"])
            <= action_time
            <= as_of
            < _parse_datetime(relationship["expires_at"])
        ):
            raise CandidatePackError("relationship evidence is not current")
    if not _parse_datetime(grant["effective_at"]) <= decided_at <= as_of < _parse_datetime(grant["expires_at"]):
        raise CandidatePackError("owner authority grant is not current")
    consumption_snapshot = _resolve_authority_phase(
        authority_resolver,
        "consumption",
        contract,
        expected_root=authority_root,
    )
    if consumption_snapshot.record_store != record_store or consumption_snapshot.record_hashes != hash_manifest:
        raise CandidatePackError("authority records changed during consumption revalidation")


def _validate_external_acceptance(
    pack: dict,
    *,
    raw_candidate_pack_bytes: bytes,
    authority_resolver: _FixtureRecordAuthority,
    review_record_id: str = REVIEW_RECORD_ID,
    owner_decision_id: str = OWNER_DECISION_ID,
    as_of: datetime = AS_OF,
) -> None:
    """Validate acceptance only against the contract authority resolved internally from Git."""
    _, trusted_contract, _ = _resolve_contract_authority()
    _validate_external_acceptance_with_authority(
        pack,
        raw_candidate_pack_bytes=raw_candidate_pack_bytes,
        contract=trusted_contract,
        trusted_contract_resolver=None,
        authority_resolver=authority_resolver,
        review_record_id=review_record_id,
        owner_decision_id=owner_decision_id,
        as_of=as_of,
    )


def _validate_hypothetical_external_acceptance(
    pack: dict,
    *,
    raw_candidate_pack_bytes: bytes,
    contract: dict,
    fixture_contract_authority: _FixtureContractAuthority,
    record_store: dict[str, dict],
    hash_manifest: dict[str, str],
    review_record_id: str = REVIEW_RECORD_ID,
    owner_decision_id: str = OWNER_DECISION_ID,
    as_of: datetime = AS_OF,
) -> None:
    """Exercise frozen hypothetical fixtures without exposing authority injection to consumers."""
    _require_issued_fixture_authority(fixture_contract_authority)
    authority_resolver = _fixture_record_authority(contract, record_store, hash_manifest)
    _validate_external_acceptance_with_authority(
        pack,
        raw_candidate_pack_bytes=raw_candidate_pack_bytes,
        contract=contract,
        trusted_contract_resolver=fixture_contract_authority,
        authority_resolver=authority_resolver,
        review_record_id=review_record_id,
        owner_decision_id=owner_decision_id,
        as_of=as_of,
    )


def test_upstream_contract_is_strict_pending_and_identity_separated():
    registry = _schema_registry()
    contract = _load_yaml(CONTRACT_PATH)
    registry.validate(CONTRACT_SCHEMA_ID, contract)
    assert registry.contains(PACK_SCHEMA_ID)
    assert registry.contains(CONTRACT_SCHEMA_ID)
    assert not registry.contains(LEGACY_GENERIC_PACK_SCHEMA_ID)
    assert contract["status"] == "pending_independent_re_review"
    assert contract["contract_revision"] == 5
    assert contract["review_gate"]["current_disposition"] == (
        "stop_for_fresh_independent_re_review_and_stephen_acceptance"
    )
    assert contract["remediation_review"]["verdict"] == "rework_required"
    assert contract["remediation_review"]["subject_commit"] == "d722664f54a55c59466a9923ac5706c7db010081"
    assert contract["remediation_review"]["report_git_blob"] == "9347c80afeb375d68e6c7e161d65c8ec3afea8fb"
    assert contract["proposed_pack_identity"]["pack_id"] == "TDL_private"
    assert contract["proposed_pack_identity"]["pack_id_semantics"] == ("accepted_domain_pack_family_name")
    assert contract["proposed_pack_identity"]["assurance_pack_object"]["id_prefix"] == "asp"
    assert contract["proposed_pack_identity"]["schema_profile"] == {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": ".research-system/schemas/assurance/assurance-pack.schema.json",
        "content_identity_location": "external_contract_review_and_owner_acceptance_records",
    }
    semantic_interface = contract["required_pack_contract"]["public_semantic_interface"]
    assert semantic_interface["required_callable"] == (
        "research_system.assurance.validate_tdl_private_pack_for_acceptance"
    )
    assert semantic_interface["implementation_status"].startswith("blocking_future_dependency")
    assert (
        contract["required_pack_contract"]["external_lifecycle"]["candidate_may_assert_review_or_acceptance"] is False
    )
    assert (
        contract["required_pack_contract"]["external_acceptance_evidence"]["candidate_may_supply_record_bodies"]
        is False
    )
    pending = {
        row["reference_id"]
        for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]
        if not row["pack_acceptance_eligible"]
    }
    assert pending == set()
    assert set(contract["required_pack_contract"]["references"]["current_pending_reference_ids"]) == pending
    _validate_pending_reference_relation(contract)
    _external_schema_catalogue(contract)
    for source in contract["source_authority"]["governing_sources"]:
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{source['git_commit']}:{source['repository_path']}"],
            cwd=ROOT,
            text=True,
        ).strip()
        assert blob == source["git_blob"]
        blob_bytes = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=ROOT)
        assert hashlib.sha256(blob_bytes).hexdigest() == source["canonical_sha256"]
        assert b"\r" not in blob_bytes
    current_reference_subjects = _current_reference_subjects(contract)
    for reference in contract["required_pack_contract"]["references"]["exact_reference_rows"]:
        assert current_reference_subjects[reference["reference_id"]] == {
            key: reference[key] for key in ("repository_path", "git_blob", "canonical_sha256")
        }
    _validate_reference_semantic_compatibility(contract)
    _assert_test_surface_closure(contract["validation_bindings"])
    _assert_all_object_schemas_are_closed(_load_json(SCHEMAS / "assurance" / "assurance-pack.schema.json"))
    _assert_all_object_schemas_are_closed(
        _load_json(SCHEMAS / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json")
    )


def test_scope_stop_future_pack_is_absent_in_remediation_task():
    assert not PACK_PATH.exists(), "the future pack remains prohibited in this remediation task"
    tracked = subprocess.run(
        ["git", "cat-file", "-e", "HEAD:.research-system/packs/tdl-private-assurance.yaml"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    assert tracked.returncode != 0


def test_external_record_schema_catalogue_rejects_missing_alias_swap_and_stale_content():
    missing = _load_yaml(CONTRACT_PATH)
    missing["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"].pop()
    with pytest.raises(CandidatePackError, match="schema class closure"):
        _external_schema_catalogue(missing)

    aliased = _load_yaml(CONTRACT_PATH)
    aliased["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"][0]["schema_id"] = (
        "ars://assurance/records/actor-alias/1.0"
    )
    with pytest.raises(CandidatePackError, match="schema identity"):
        _external_schema_catalogue(aliased)

    swapped = _load_yaml(CONTRACT_PATH)
    rows = swapped["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"]
    rows[0]["schema_json_pointer"], rows[1]["schema_json_pointer"] = (
        rows[1]["schema_json_pointer"],
        rows[0]["schema_json_pointer"],
    )
    with pytest.raises(CandidatePackError, match="pointer identity"):
        _external_schema_catalogue(swapped)

    stale_content = _load_yaml(CONTRACT_PATH)
    stale_content["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"][0][
        "schema_git_blob"
    ] = "f" * 40
    with pytest.raises(CandidatePackError, match="content identity"):
        _external_schema_catalogue(stale_content)


def test_candidate_schema_is_proposed_only_and_has_no_acceptance_surface():
    pack = _proposed_pack()
    _validate_proposed_pack(pack)
    assert pack["candidate_state"] == "proposed"
    forbidden = {
        "accepted",
        "review_record_hash",
        "acceptance_decision_hash",
        "acceptor_actor_id",
        "scientific_reviewer_actor_id",
        "pack_content_sha256",
    }
    assert not forbidden & set(pack)

    self_accepted = deepcopy(pack)
    self_accepted["candidate_state"] = "accepted"
    with pytest.raises(SchemaError, match="candidate_state"):
        _validate_proposed_pack(self_accepted)

    self_review = deepcopy(pack)
    self_review["review_record_hash"] = "f" * 64
    with pytest.raises(SchemaError, match="review_record_hash"):
        _validate_proposed_pack(self_review)

    producer_only_na = deepcopy(pack)
    producer_only_na["lanes"]["topology"]["not_applicable"] = {
        "author_actor_id": ACT_PRODUCER,
        "confirming_actor_id": ACT_PRODUCER,
    }
    with pytest.raises(SchemaError, match="not_applicable"):
        _validate_proposed_pack(producer_only_na)


def test_external_acceptance_requires_independent_exact_subject_records():
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    _validate_hypothetical_external_acceptance(
        pack,
        raw_candidate_pack_bytes=raw_candidate_pack_bytes,
        contract=contract,
        fixture_contract_authority=contract_resolver,
        record_store=record_store,
        hash_manifest=hash_manifest,
    )

    same_author_pack = deepcopy(pack)
    same_author = deepcopy(record_store)
    same_author[REQUIREMENT_RECORD_ID]["requirement_author_actor_id"] = ACT_PRODUCER
    for applicability in same_author[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"]:
        applicability["decision_author_actor_id"] = ACT_PRODUCER
    same_author_raw, same_author_hashes = _coordinate_all_external_hashes(same_author_pack, same_author)
    with pytest.raises(CandidatePackError, match="must be distinct"):
        _validate_hypothetical_external_acceptance(
            same_author_pack,
            raw_candidate_pack_bytes=same_author_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=same_author,
            hash_manifest=same_author_hashes,
        )

    wrong_review_subject = deepcopy(record_store)
    wrong_review_hashes = deepcopy(hash_manifest)
    wrong_review_subject[REVIEW_RECORD_ID]["subject"]["pack_raw_sha256"] = "f" * 64
    _rehash_record(wrong_review_subject, wrong_review_hashes, REVIEW_RECORD_ID)
    wrong_review_subject[OWNER_DECISION_ID]["review_record_sha256"] = wrong_review_hashes[REVIEW_RECORD_ID]
    _rehash_record(wrong_review_subject, wrong_review_hashes, OWNER_DECISION_ID)
    with pytest.raises(CandidatePackError, match="review subject"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=wrong_review_subject,
            hash_manifest=wrong_review_hashes,
        )

    wrong_owner_subject = deepcopy(record_store)
    wrong_owner_hashes = deepcopy(hash_manifest)
    wrong_owner_subject[OWNER_DECISION_ID]["subject"]["pack_git_blob"] = "f" * 40
    _rehash_record(wrong_owner_subject, wrong_owner_hashes, OWNER_DECISION_ID)
    with pytest.raises(CandidatePackError, match="owner decision subject"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=wrong_owner_subject,
            hash_manifest=wrong_owner_hashes,
        )

    no_owner_grant = deepcopy(record_store)
    no_owner_grant.pop(OWNER_GRANT_ID)
    with pytest.raises(CandidatePackError, match="missing external record"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=no_owner_grant,
            hash_manifest=hash_manifest,
        )

    actor_alias = deepcopy(pack)
    actor_alias["producer_actor_id"] = "act_future_pack_producer"
    actor_alias["assurance_requirement_reference"]["prospective_producer_actor_id"] = "act_future_pack_producer"
    with pytest.raises(SchemaError, match="producer_actor_id"):
        _validate_hypothetical_external_acceptance(
            actor_alias,
            raw_candidate_pack_bytes=_raw_pack_bytes(actor_alias),
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_hash_valid_external_record_semantic_mutations_are_rejected():
    mutations = {
        "rejected requirement": lambda records: records[REQUIREMENT_RECORD_ID].update(outcome="rejected"),
        "producer accepts requirement": lambda records: records[REQUIREMENT_RECORD_ID].update(
            acceptor_actor_id=ACT_PRODUCER
        ),
        "requirement accepted after owner": lambda records: records[REQUIREMENT_RECORD_ID].update(
            accepted_at="2026-07-18T11:30:00Z"
        ),
        "foreign requirement record type": lambda records: records[REQUIREMENT_RECORD_ID].update(
            record_type="foreign_requirement"
        ),
        "foreign owner record type": lambda records: records[OWNER_DECISION_ID].update(
            record_type="foreign_owner_decision"
        ),
        "wrong review producer": lambda records: records[REVIEW_RECORD_ID].update(
            producer_actor_id=ACT_REQUIREMENT_AUTHOR
        ),
        "role-like reviewer alias": lambda records: records[REVIEW_RECORD_ID].update(
            reviewer_actor_id="pack_scientific_reviewer"
        ),
        "inactive canonical actor": lambda records: records[ACT_SCIENTIFIC_REVIEWER].update(status="inactive"),
        "foreign authority class": lambda records: records[OWNER_GRANT_ID].update(
            authority_class="foreign_owner_authority"
        ),
        "relationship substitution": lambda records: records[REVIEW_RECORD_ID].update(
            relationship_record_id=SCOPE_RELATIONSHIP_ID
        ),
        "review before candidate": lambda records: records[REVIEW_RECORD_ID].update(reviewed_at="2026-07-18T08:50:00Z"),
    }
    for _label, mutate in mutations.items():
        contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
        mutate(record_store)
        raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
        with pytest.raises(CandidatePackError):
            _validate_hypothetical_external_acceptance(
                pack,
                raw_candidate_pack_bytes=raw_candidate_pack_bytes,
                contract=contract,
                fixture_contract_authority=contract_resolver,
                record_store=record_store,
                hash_manifest=hash_manifest,
            )


def test_raw_candidate_bytes_define_portable_review_subject():
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    baseline_subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    assert baseline_subject["pack_git_blob"] == _git_blob_id_without_filters(raw_candidate_pack_bytes)
    assert baseline_subject["pack_raw_sha256"] == hashlib.sha256(raw_candidate_pack_bytes).hexdigest()

    equivalent_bytes = [
        _raw_pack_bytes(pack, leading_comment="semantically equivalent but byte-distinct"),
        _raw_pack_bytes(pack, reverse_top_level=True),
        raw_candidate_pack_bytes.replace(b"schema_version:", b"\nschema_version:", 1),
    ]
    for candidate_bytes in equivalent_bytes:
        assert _parse_candidate_pack_bytes(candidate_bytes) == pack
        subject = _pack_subject(candidate_bytes, expected_pack=pack)
        assert subject != baseline_subject
        assert subject["pack_git_blob"] == _git_blob_id_without_filters(candidate_bytes)
        with pytest.raises(CandidatePackError, match="review subject"):
            _validate_hypothetical_external_acceptance(
                pack,
                raw_candidate_pack_bytes=candidate_bytes,
                contract=contract,
                fixture_contract_authority=contract_resolver,
                record_store=record_store,
                hash_manifest=hash_manifest,
            )


def test_exact_reference_set_rejects_missing_extra_duplicate_alias_swap_and_foreign_rows():
    base = _proposed_pack()

    missing = deepcopy(base)
    missing["references"]["contract_references"].pop()
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(missing)

    foreign = deepcopy(base)
    foreign_row = deepcopy(foreign["references"]["contract_references"][0])
    foreign_row["reference_id"] = "contract/foreign/shape-valid"
    foreign_row["repository_path"] = "contracts/foreign/shape-valid.yaml"
    foreign["references"]["contract_references"][0] = foreign_row
    with pytest.raises(CandidatePackError, match="exact upstream set"):
        _validate_proposed_pack(foreign)

    duplicate = deepcopy(base)
    duplicate_row = deepcopy(duplicate["references"]["contract_references"][0])
    duplicate_row["canonical_sha256"] = "f" * 64
    duplicate["references"]["contract_references"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate reference id"):
        _validate_proposed_pack(duplicate)

    alias = deepcopy(base)
    alias["references"]["skill_references"][0]["reference_id"] = "skill/validate_topology"
    with pytest.raises(CandidatePackError, match="exact upstream set"):
        _validate_proposed_pack(alias)

    kind_swap = deepcopy(base)
    contract_row = kind_swap["references"]["contract_references"].pop()
    skill_row = kind_swap["references"]["skill_references"].pop()
    kind_swap["references"]["contract_references"].append(skill_row)
    kind_swap["references"]["skill_references"].append(contract_row)
    with pytest.raises(SchemaError):
        _validate_proposed_pack(kind_swap)

    copied = deepcopy(base)
    copied["references"]["skill_references"][0]["inline_body"] = True
    with pytest.raises(SchemaError, match="inline_body"):
        _validate_proposed_pack(copied)


def test_lane_reference_relations_reject_dangling_swapped_and_pending_rows():
    contract = _load_yaml(CONTRACT_PATH)
    for lane_id in ("topology", "statistical_panel", "output_provenance"):
        assert (
            "skill/paper-claim-trace"
            in contract["required_pack_contract"]["lanes"][lane_id]["exact_governing_reference_ids"]
        )

    dangling = _proposed_pack()
    dangling["lanes"]["topology"]["governing_reference_ids"][0] = "skill/foreign-valid"
    with pytest.raises(CandidatePackError, match="lane reference relation"):
        _validate_proposed_pack(dangling)

    swapped = _proposed_pack()
    swapped["lanes"]["representation"]["governing_reference_ids"] = deepcopy(
        swapped["lanes"]["topology"]["governing_reference_ids"]
    )
    with pytest.raises(CandidatePackError, match="lane reference relation"):
        _validate_proposed_pack(swapped)

    pending_contract = _load_yaml(CONTRACT_PATH)
    pending_id = "contract/topology-invariants/null-operation-changes-ph-input"
    pending_row = next(
        row
        for row in pending_contract["required_pack_contract"]["references"]["exact_reference_rows"]
        if row["reference_id"] == pending_id
    )
    pending_row["activation_state"] = "pending"
    pending_row["pack_acceptance_eligible"] = False
    pending_contract["required_pack_contract"]["references"]["current_pending_reference_ids"] = [pending_id]
    pending_resolver = _fixture_contract_authority(pending_contract)
    _, _, pending_subject = _resolve_contract_authority(pending_resolver)
    current_pending = _proposed_pack(pending_contract, contract_subject=pending_subject)
    with pytest.raises(CandidatePackError, match="pending reference blocks"):
        _validate_hypothetical_proposed_pack(
            current_pending,
            contract=pending_contract,
            fixture_contract_authority=pending_resolver,
            require_active_references=True,
        )

    eligible_contract = _eligible_contract()
    _schema_registry().validate(CONTRACT_SCHEMA_ID, eligible_contract)
    assert eligible_contract["required_pack_contract"]["references"]["current_pending_reference_ids"] == []
    _validate_pending_reference_relation(eligible_contract)
    eligible_contract_resolver = _fixture_contract_authority(eligible_contract)
    _, _, eligible_contract_subject = _resolve_contract_authority(eligible_contract_resolver)
    eligible = _proposed_pack(eligible_contract, contract_subject=eligible_contract_subject)
    _validate_hypothetical_proposed_pack(
        eligible,
        contract=eligible_contract,
        fixture_contract_authority=eligible_contract_resolver,
        require_active_references=True,
    )

    missing_pending = _load_yaml(CONTRACT_PATH)
    missing_row = missing_pending["required_pack_contract"]["references"]["exact_reference_rows"][1]
    missing_row["activation_state"] = "pending"
    missing_row["pack_acceptance_eligible"] = False
    missing_pending_resolver = _fixture_contract_authority(missing_pending)
    _, _, missing_pending_subject = _resolve_contract_authority(missing_pending_resolver)
    with pytest.raises(CandidatePackError, match="pending reference relation"):
        _validate_hypothetical_proposed_pack(
            _proposed_pack(missing_pending, contract_subject=missing_pending_subject),
            contract=missing_pending,
            fixture_contract_authority=missing_pending_resolver,
        )

    stale_pending = _eligible_contract()
    stale_pending["required_pack_contract"]["references"]["current_pending_reference_ids"].append(
        "contract/topology-invariants/null-operation-changes-ph-input"
    )
    _schema_registry().validate(CONTRACT_SCHEMA_ID, stale_pending)
    stale_pending_resolver = _fixture_contract_authority(stale_pending)
    _, _, stale_pending_subject = _resolve_contract_authority(stale_pending_resolver)
    with pytest.raises(CandidatePackError, match="pending reference relation"):
        _validate_hypothetical_proposed_pack(
            _proposed_pack(stale_pending, contract_subject=stale_pending_subject),
            contract=stale_pending,
            fixture_contract_authority=stale_pending_resolver,
        )

    omitted_contract = _load_yaml(CONTRACT_PATH)
    omitted_contract["required_pack_contract"]["lanes"]["topology"]["exact_governing_reference_ids"].remove(
        "skill/paper-claim-trace"
    )
    omitted_contract_resolver = _fixture_contract_authority(omitted_contract)
    _, _, omitted_contract_subject = _resolve_contract_authority(omitted_contract_resolver)
    omitted_pack = _proposed_pack(omitted_contract, contract_subject=omitted_contract_subject)
    with pytest.raises(CandidatePackError, match="enforcer is omitted"):
        _validate_hypothetical_proposed_pack(
            omitted_pack,
            contract=omitted_contract,
            fixture_contract_authority=omitted_contract_resolver,
        )

    foreign_valid = _proposed_pack()
    interpretation = next(
        row
        for row in foreign_valid["lanes"]["topology"]["obligation_rows"]
        if row["obligation_id"] == "topology.interpretation_topology_geometry_association_causality"
    )
    interpretation["enforcing_reference_ids"][-1] = "skill/research-assurance-triage"
    with pytest.raises(CandidatePackError, match="obligation rows"):
        _validate_proposed_pack(foreign_valid)


def test_exact_fixture_set_rejects_missing_extra_duplicate_and_attack_swaps():
    missing = _proposed_pack()
    missing["required_fixtures"].pop()
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(missing)

    extra = _proposed_pack()
    extra_row = deepcopy(extra["required_fixtures"][0])
    extra_row["fixture_id"] = "apf_foreign_shape_valid"
    extra["required_fixtures"].append(extra_row)
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(extra)

    duplicate = _proposed_pack()
    duplicate_row = deepcopy(duplicate["required_fixtures"][0])
    duplicate_row["attack_class"] = "extra"
    duplicate["required_fixtures"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate fixture id"):
        _validate_proposed_pack(duplicate)

    attack_swap = _proposed_pack()
    attack_swap["required_fixtures"][0]["attack_class"] = "authority"
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(attack_swap)


def test_no_op_degenerate_and_claim_escalation_rows_have_upstream_negatives_and_downstream_stop():
    contract = _load_yaml(CONTRACT_PATH)
    boundary = contract["required_pack_contract"]["fixture_execution_boundary"]
    assert boundary["upstream_executable_fixture_ids"] == [
        "apf_tested_object_no_op",
        "apf_degenerate_fallback",
        "apf_claim_escalation",
    ]
    assert boundary["downstream_enforcement_status"].startswith("hard_stop_requires_distinct_future_producer")
    assert boundary["upstream_may_claim_downstream_execution"] is False

    no_op = _proposed_pack()
    no_op["required_fixtures"] = [
        row for row in no_op["required_fixtures"] if row["fixture_id"] != "apf_tested_object_no_op"
    ]
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(no_op)

    degenerate = _proposed_pack()
    next(row for row in degenerate["required_fixtures"] if row["fixture_id"] == "apf_degenerate_fallback")[
        "expected_outcome"
    ] = "accepted"
    with pytest.raises(SchemaError, match="expected_outcome"):
        _validate_proposed_pack(degenerate)

    claim_escalation = _proposed_pack()
    claim_escalation["core_boundary"]["may_promote_claims"] = True
    with pytest.raises(SchemaError, match="may_promote_claims"):
        _validate_proposed_pack(claim_escalation)


def test_complete_w5_obligation_rows_reject_missing_duplicate_swap_and_free_text():
    pack = _proposed_pack()
    for lane_id, expected_ids in EXPECTED_OBLIGATION_IDS.items():
        assert {row["obligation_id"] for row in pack["lanes"][lane_id]["obligation_rows"]} == (expected_ids)

    missing = _proposed_pack()
    missing["lanes"]["topology"]["obligation_rows"].pop()
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(missing)

    duplicate = _proposed_pack()
    duplicate_row = deepcopy(duplicate["lanes"]["topology"]["obligation_rows"][0])
    duplicate_row["review_question_id"] = "review.topology.duplicate_alias"
    duplicate["lanes"]["topology"]["obligation_rows"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate obligation id"):
        _validate_proposed_pack(duplicate)

    swapped = _proposed_pack()
    swapped["lanes"]["topology"]["obligation_rows"][0], swapped["lanes"]["representation"]["obligation_rows"][0] = (
        swapped["lanes"]["representation"]["obligation_rows"][0],
        swapped["lanes"]["topology"]["obligation_rows"][0],
    )
    with pytest.raises(CandidatePackError, match="obligation rows"):
        _validate_proposed_pack(swapped)

    free_text = _proposed_pack()
    free_text["lanes"]["topology"]["obligation_rows"][0]["obligation_text"] = "Explicit prospective obligation."
    with pytest.raises(SchemaError, match="obligation_text"):
        _validate_proposed_pack(free_text)


def test_distribution_currency_and_identity_mutations_fail_closed():
    wrong_scope = _proposed_pack()
    wrong_scope["distribution_scope"] = "template_safe"
    with pytest.raises(SchemaError, match="distribution_scope"):
        _validate_proposed_pack(wrong_scope)

    widened = _proposed_pack()
    widened["distribution_controls"]["permitted_consumers"].append("public_template_exporter")
    with pytest.raises(SchemaError, match="permitted_consumers"):
        _validate_proposed_pack(widened)

    for missing_field in ("permitted_consumers", "publication_boundary", "path_restrictions", "data_restrictions"):
        missing = _proposed_pack()
        del missing["distribution_controls"][missing_field]
        with pytest.raises(SchemaError, match=missing_field):
            _validate_proposed_pack(missing)

    contradictory = _proposed_pack()
    contradictory["distribution_controls"]["path_restrictions"]["public_template_paths"] = "allowed"
    with pytest.raises(SchemaError, match="public_template_paths"):
        _validate_proposed_pack(contradictory)

    inverted = _proposed_pack()
    inverted["currency"]["effective_at"] = "2028-01-01T00:00:00Z"
    with pytest.raises(CandidatePackError, match="time order"):
        _validate_proposed_pack(inverted)

    expired = _proposed_pack()
    expired["currency"]["authored_at"] = "2026-07-15T00:00:00Z"
    expired["currency"]["effective_at"] = "2026-07-16T00:00:00Z"
    expired["currency"]["expires_at"] = "2026-07-17T00:00:00Z"
    with pytest.raises(CandidatePackError, match="expired"):
        _validate_proposed_pack(expired)

    stale_contract = _proposed_pack()
    stale_contract["upstream_contract_reference"]["canonical_sha256"] = "f" * 64
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(stale_contract)

    schema_swap = _proposed_pack()
    schema_swap["schema_reference"]["git_blob"] = "f" * 40
    with pytest.raises(CandidatePackError, match="stale pack schema subject"):
        _validate_proposed_pack(schema_swap)

    object_alias = _proposed_pack()
    object_alias["assurance_pack_id"] = "TDL_private"
    with pytest.raises(SchemaError, match="assurance_pack_id"):
        _validate_proposed_pack(object_alias)

    producer_change = _proposed_pack()
    producer_change["producer_actor_id"] = ACT_SCIENTIFIC_REVIEWER
    with pytest.raises(CandidatePackError, match="prospective producer relationship is stale"):
        _validate_proposed_pack(producer_change)


def test_coordinated_candidate_and_oracle_replacement_does_not_change_external_authority():
    coordinated_contract = _eligible_contract()
    coordinated_contract["required_pack_contract"]["references"]["exact_reference_rows"][0]["git_blob"] = "7" * 40
    coordinated_contract["required_pack_contract"]["references"]["exact_reference_rows"][0]["canonical_sha256"] = (
        "8" * 64
    )
    coordinated_resolver = _fixture_contract_authority(coordinated_contract)
    _, _, coordinated_subject = _resolve_contract_authority(coordinated_resolver)
    coordinated_candidate = _proposed_pack(
        coordinated_contract,
        contract_subject=coordinated_subject,
    )
    with pytest.raises(CandidatePackError, match="trusted Git contract authority"):
        _validate_proposed_pack(
            coordinated_candidate,
            contract=coordinated_contract,
            require_active_references=True,
        )

    accepted_contract = _load_yaml(CONTRACT_PATH)
    candidate = _proposed_pack(accepted_contract)
    expected_row = accepted_contract["required_pack_contract"]["references"]["exact_reference_rows"][0]
    expected_row["canonical_sha256"] = "f" * 64
    candidate_row = candidate["references"]["contract_references"][0]
    candidate_row["canonical_sha256"] = "f" * 64
    with pytest.raises(CandidatePackError, match="trusted Git contract authority"):
        _validate_proposed_pack(
            candidate,
            contract=accepted_contract,
        )

    eligible_contract = _eligible_contract()
    eligible_contract_resolver = _fixture_contract_authority(eligible_contract)
    _, _, eligible_contract_subject = _resolve_contract_authority(eligible_contract_resolver)
    eligible_pack = _proposed_pack(
        eligible_contract,
        contract_subject=eligible_contract_subject,
    )
    pack, raw_candidate_pack_bytes, record_store, hash_manifest = _external_records(eligible_pack, eligible_contract)
    public_acceptance_parameters = inspect.signature(_validate_external_acceptance).parameters
    assert "contract" not in public_acceptance_parameters
    assert "trusted_contract_resolver" not in public_acceptance_parameters
    assert "fixture_contract_authority" not in public_acceptance_parameters
    assert "record_store" not in public_acceptance_parameters
    assert "hash_manifest" not in public_acceptance_parameters
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            authority_resolver=_fixture_record_authority(eligible_contract, record_store, hash_manifest),
        )
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        caller_controlled_authority = {"trusted_contract_resolver": eligible_contract_resolver}
        runtime_public_acceptance = globals()["_validate_external_acceptance"]
        runtime_public_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            authority_resolver=_fixture_record_authority(eligible_contract, record_store, hash_manifest),
            **caller_controlled_authority,
        )
    tampered_pack = deepcopy(pack)
    tampered_pack["currency"]["expires_at"] = "2028-07-18T09:00:00Z"
    tampered_review = deepcopy(record_store)
    tampered_raw, _ = _coordinate_all_external_hashes(tampered_pack, tampered_review)
    frozen_external_manifest = deepcopy(hash_manifest)
    with pytest.raises(CandidatePackError, match="external record hash mismatch"):
        _validate_hypothetical_external_acceptance(
            tampered_pack,
            raw_candidate_pack_bytes=tampered_raw,
            contract=eligible_contract,
            fixture_contract_authority=eligible_contract_resolver,
            record_store=tampered_review,
            hash_manifest=frozen_external_manifest,
        )


def test_external_schema_identity_resolves_via_git_object_oracle_across_crlf_and_lf_checkouts():
    """R3-M1 regression: schema content identity must come from the frozen Git blob,
    not from whatever bytes the current checkout's line-ending filters produced."""
    _external_schema_artifact.cache_clear()
    schema_document, schema_blob, schema_sha256 = _external_schema_artifact()
    repo_relative_path = _repo_relative_path(CONTRACT_SCHEMA_PATH)
    current_subject = _resolve_current_repository_subject(CONTRACT_SCHEMA_PATH)
    head_blob = _git_head_blob_id(repo_relative_path)
    assert schema_blob == current_subject["git_blob"]
    assert schema_sha256 == current_subject["canonical_sha256"]
    committed_bytes = _git_blob_bytes(head_blob)
    assert schema_document["$defs"]["canonicalActorRecord"]["$id"] == ("ars://assurance/records/canonical-actor/1.0")

    # A CRLF working-tree variant of this exact LF blob: under `core.autocrlf=true` (the
    # repository's normal Windows checkout) Git's own clean filter (`git hash-object
    # --path`) renormalizes it back to the committed blob, so it must resolve
    # identically to HEAD there — this is exactly the R3-M1 defect this test guards.
    # Under `core.autocrlf=false` (this test's own possibly-different checkout, e.g. a
    # fresh LF verification clone) the same filter does not renormalize it, so the CRLF
    # bytes are a genuine content difference and must be rejected as dirty instead.
    # Rather than hardcoding one behavior, this asks Git itself which regime is active
    # (per Observation 71: measure with the tool that reports the state, don't assume
    # from a proxy) and asserts the resolver agrees with Git's own live filter verdict.
    crlf_working_tree_bytes = committed_bytes.replace(b"\n", b"\r\n")
    assert crlf_working_tree_bytes != committed_bytes
    crlf_filtered_blob = (
        subprocess.check_output(
            ["git", "hash-object", "--path", repo_relative_path, "--stdin"],
            input=crlf_working_tree_bytes,
            cwd=ROOT,
        )
        .decode()
        .strip()
    )
    if crlf_filtered_blob == head_blob:
        crlf_bytes, crlf_blob = _resolve_committed_bytes(
            CONTRACT_SCHEMA_PATH, working_tree_bytes=crlf_working_tree_bytes
        )
        assert crlf_blob == head_blob
        assert crlf_bytes == committed_bytes
    else:
        with pytest.raises(CandidatePackError, match="dirty or uncommitted"):
            _resolve_committed_bytes(CONTRACT_SCHEMA_PATH, working_tree_bytes=crlf_working_tree_bytes)

    # An LF checkout (working-tree bytes identical to the committed blob) resolves the
    # same way — the oracle is checkout-representation-invariant in both directions.
    lf_bytes, lf_blob = _resolve_committed_bytes(CONTRACT_SCHEMA_PATH, working_tree_bytes=committed_bytes)
    assert lf_blob == head_blob
    assert lf_bytes == committed_bytes
    _external_schema_artifact.cache_clear()


def test_default_contract_authority_resolves_current_subject_once(monkeypatch):
    """The default resolver must reuse one subject snapshot for bytes and metadata."""
    real_resolver = _resolve_current_repository_subject
    real_blob_reader = _git_blob_bytes
    calls: list[Path] = []
    blob_reads: list[str] = []

    def counting_resolver(path: Path) -> dict:
        calls.append(path)
        return real_resolver(path)

    def counting_blob_reader(blob_oid: str) -> bytes:
        blob_reads.append(blob_oid)
        return real_blob_reader(blob_oid)

    monkeypatch.setattr(
        "test_wp6_3_tdl_private_assurance_pack_contract._resolve_current_repository_subject",
        counting_resolver,
    )
    monkeypatch.setattr(
        "test_wp6_3_tdl_private_assurance_pack_contract._git_blob_bytes",
        counting_blob_reader,
    )
    _resolve_contract_authority()
    assert calls == [CONTRACT_PATH]
    assert len(blob_reads) == 1


def test_external_schema_artifact_reuses_current_subject_blob_bytes(monkeypatch):
    """The external schema resolver must not fetch its canonical blob twice."""
    real_resolver = _resolve_current_repository_subject
    real_blob_reader = _git_blob_bytes
    subjects: list[dict] = []
    blob_reads: list[str] = []

    def counting_resolver(path: Path) -> dict:
        subject = real_resolver(path)
        subjects.append(subject)
        return subject

    def counting_blob_reader(blob_oid: str) -> bytes:
        blob_reads.append(blob_oid)
        return real_blob_reader(blob_oid)

    monkeypatch.setattr(
        "test_wp6_3_tdl_private_assurance_pack_contract._resolve_current_repository_subject",
        counting_resolver,
    )
    monkeypatch.setattr(
        "test_wp6_3_tdl_private_assurance_pack_contract._git_blob_bytes",
        counting_blob_reader,
    )
    _external_schema_artifact.cache_clear()
    _external_schema_artifact()
    _external_schema_artifact.cache_clear()
    assert [subject["repository_path"] for subject in subjects] == [_repo_relative_path(CONTRACT_SCHEMA_PATH)]
    assert len(blob_reads) == 1


@pytest.mark.parametrize(
    "forbidden_wording",
    [
        "The p value is the empirical proportion of null-to-null distances.",
        "Use a fixed 500 null pair diagnostic sample as the p value denominator.",
    ],
)
def test_reference_semantic_compatibility_rejects_forbidden_wording_variations(monkeypatch, forbidden_wording):
    """Contract-defined forbidden semantics must survive harmless wording variation."""
    skill_path = ROOT / ".agents" / "skills" / "validate-topology" / "SKILL.md"
    original_read_text = Path.read_text
    original_skill_text = skill_path.read_text(encoding="utf-8")

    def read_text_with_forbidden_semantics(path: Path, *args, **kwargs) -> str:
        if path == skill_path:
            return f"{original_skill_text}\n{forbidden_wording}\n"
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text_with_forbidden_semantics)
    with pytest.raises(CandidatePackError, match="semantically incompatible"):
        _validate_reference_semantic_compatibility(_load_yaml(CONTRACT_PATH))


def test_dirty_or_uncommitted_schema_bytes_are_rejected_by_a_distinct_check():
    """R3-M1: dirty/uncommitted candidate bytes must be a separate, explicit rejection
    path from content-identity resolution — a real edit (not a line-ending checkout
    variant) never resolves to the frozen HEAD blob under Git's own clean filter."""
    repo_relative_path = _repo_relative_path(CONTRACT_SCHEMA_PATH)
    head_blob = _git_head_blob_id(repo_relative_path)
    committed_bytes = _git_blob_bytes(head_blob)
    dirty_bytes = committed_bytes + b"\n// locally edited, uncommitted\n"
    with pytest.raises(CandidatePackError, match="dirty or uncommitted"):
        _resolve_committed_bytes(CONTRACT_SCHEMA_PATH, working_tree_bytes=dirty_bytes)

    truncated_bytes = committed_bytes[:-1]
    with pytest.raises(CandidatePackError, match="dirty or uncommitted"):
        _resolve_committed_bytes(CONTRACT_SCHEMA_PATH, working_tree_bytes=truncated_bytes)


def test_upstream_contract_and_schema_subjects_resist_stale_foreign_and_coordinated_replacement():
    """R3-M2 regression: the accepted contract/schema content addresses are resolved
    from the Git object store, so they are never the fixed placeholders a candidate
    could freely match; stale, foreign-but-real, swapped, and coordinated-replacement
    attempts must all fail against the independently resolved identity."""
    real_contract_reference = _resolve_external_contract_reference()
    real_schema_reference = _resolve_external_schema_reference()

    # Sanity: the resolved references are the actual committed objects, not the R2
    # placeholders (all-`1`/`2`/`3`/`4` digit strings) the R3 review found accepted.
    assert real_contract_reference["git_blob"] != "1" * 40
    assert real_contract_reference["canonical_sha256"] != "2" * 64
    assert real_schema_reference["git_blob"] != "3" * 40
    assert real_schema_reference["canonical_sha256"] != "4" * 64
    # The resolved identity is never a literal pinned in this test file either — it is
    # cross-checked here against a fully independent, freshly invoked `git` call, so an
    # edit to either committed file (this remediation edits both) changes what both
    # sides compute together rather than leaving a stale hardcoded expectation behind.
    independent_contract_path = _repo_relative_path(CONTRACT_PATH)
    independent_contract_blob = (
        subprocess.check_output(["git", "rev-parse", f"HEAD:{independent_contract_path}"], cwd=ROOT).decode().strip()
    )
    independent_contract_bytes = subprocess.check_output(
        ["git", "cat-file", "blob", independent_contract_blob], cwd=ROOT
    )
    assert real_contract_reference["git_blob"] == independent_contract_blob
    assert real_contract_reference["canonical_sha256"] == hashlib.sha256(independent_contract_bytes).hexdigest()

    independent_schema_path = _repo_relative_path(SCHEMAS / "assurance" / "assurance-pack.schema.json")
    independent_schema_blob = (
        subprocess.check_output(["git", "rev-parse", f"HEAD:{independent_schema_path}"], cwd=ROOT).decode().strip()
    )
    independent_schema_bytes = subprocess.check_output(["git", "cat-file", "blob", independent_schema_blob], cwd=ROOT)
    assert real_schema_reference["git_blob"] == independent_schema_blob
    assert real_schema_reference["canonical_sha256"] == hashlib.sha256(independent_schema_bytes).hexdigest()

    baseline = _proposed_pack()
    _validate_proposed_pack(baseline)

    # stale: a plausible-looking but non-current identity.
    stale = _proposed_pack()
    stale["upstream_contract_reference"]["git_blob"] = "0" * 40
    stale["upstream_contract_reference"]["canonical_sha256"] = "0" * 64
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(stale)

    # foreign-valid: a real, currently-committed content address for a *different*
    # artifact substituted onto the contract subject field.
    foreign_valid = _proposed_pack()
    foreign_valid["upstream_contract_reference"]["git_blob"] = real_schema_reference["git_blob"]
    foreign_valid["upstream_contract_reference"]["canonical_sha256"] = real_schema_reference["canonical_sha256"]
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(foreign_valid)

    # swapped: contract and schema subjects exchange each other's real identities.
    swapped = _proposed_pack()
    swapped["upstream_contract_reference"]["git_blob"] = real_schema_reference["git_blob"]
    swapped["upstream_contract_reference"]["canonical_sha256"] = real_schema_reference["canonical_sha256"]
    swapped["schema_reference"]["git_blob"] = real_contract_reference["git_blob"]
    swapped["schema_reference"]["canonical_sha256"] = real_contract_reference["canonical_sha256"]
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(swapped)

    # coordinated replacement of both subjects to a shared, internally-consistent but
    # wrong pair of real identities must still fail.
    coordinated = _proposed_pack()
    coordinated["upstream_contract_reference"]["git_blob"] = real_schema_reference["git_blob"]
    coordinated["upstream_contract_reference"]["canonical_sha256"] = real_schema_reference["canonical_sha256"]
    coordinated["schema_reference"]["git_blob"] = real_schema_reference["git_blob"]
    coordinated["schema_reference"]["canonical_sha256"] = real_schema_reference["canonical_sha256"]
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(coordinated)


def test_requirement_reference_binds_single_authoritative_content_hash():
    """R3-M3 design choice: the seven-record design already resolves and hash-checks
    the full accepted-requirement record body through `acceptance_record_sha256`
    (`_resolved_record` / `_validate_external_acceptance`), so `acceptance_record_sha256`
    is kept as the single authoritative content identity for the requirement subject.
    The previously-present `canonical_sha256` field on `assurance_requirement_reference`
    was redundant with it, was never joined to the resolved requirement, and has been
    removed from the schema rather than independently bound — removing a duplicate
    unenforced authority is preferred over adding a second one to reconcile."""
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    assert "canonical_sha256" not in pack["assurance_requirement_reference"]
    _validate_hypothetical_external_acceptance(
        pack,
        raw_candidate_pack_bytes=raw_candidate_pack_bytes,
        contract=contract,
        fixture_contract_authority=contract_resolver,
        record_store=record_store,
        hash_manifest=hash_manifest,
    )

    # Reintroducing the removed field is now a structural rejection (unknown property),
    # not a silently-ignored one — this is the R3-M3 reproduction fixture
    # (`"5" * 64` -> `"a" * 64`) made impossible rather than merely unwatched.
    reintroduced = deepcopy(pack)
    reintroduced["assurance_requirement_reference"]["canonical_sha256"] = "a" * 64
    with pytest.raises(SchemaError, match="canonical_sha256"):
        _validate_hypothetical_proposed_pack(
            reintroduced,
            contract=contract,
            fixture_contract_authority=contract_resolver,
        )

    # one-field substitution: candidate claims an acceptance_record_sha256 that does
    # not match the resolved external requirement record's actual content hash.
    one_field = deepcopy(pack)
    one_field["assurance_requirement_reference"]["acceptance_record_sha256"] = "f" * 64
    one_field_raw = _raw_pack_bytes(one_field)
    with pytest.raises(CandidatePackError, match="does not match external record"):
        _validate_hypothetical_external_acceptance(
            one_field,
            raw_candidate_pack_bytes=one_field_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    # coordinated rehash: the accepted requirement's bound upstream-contract subject is
    # replaced, the requirement record and every downstream (review/owner) subject are
    # recomputed and rehashed together, and the candidate's acceptance_record_sha256 is
    # kept internally consistent throughout. The independently-resolved subject_contract
    # check still catches it, because the oracle is external to the candidate/record
    # chain rather than reproduced from within it.
    coordinated_store = deepcopy(record_store)
    coordinated_store[REQUIREMENT_RECORD_ID]["subject_contract"] = {
        **deepcopy(coordinated_store[REQUIREMENT_RECORD_ID]["subject_contract"]),
        "git_blob": "f" * 40,
        "canonical_sha256": "f" * 64,
    }
    coordinated_pack = deepcopy(pack)
    coordinated_raw, coordinated_hashes = _coordinate_all_external_hashes(coordinated_pack, coordinated_store)
    with pytest.raises(CandidatePackError, match="different upstream contract"):
        _validate_hypothetical_external_acceptance(
            coordinated_pack,
            raw_candidate_pack_bytes=coordinated_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=coordinated_store,
            hash_manifest=coordinated_hashes,
        )


def test_contract_schema_lifecycle_requires_content_addressed_external_authority_records():
    """Contract/schema bytes are eligible only through typed external lifecycle records."""
    contract = _load_yaml(CONTRACT_PATH)
    required_record_types = set(
        contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    )
    schema_rows = {
        row["record_class"]
        for row in contract["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"]
    }
    lifecycle_record_types = {
        "contract_schema_authorship",
        "independent_contract_review",
        "independent_schema_review",
        "stephen_contract_schema_acceptance",
    }
    assert lifecycle_record_types <= required_record_types
    assert lifecycle_record_types <= schema_rows

    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    for missing_record_id in (
        CONTRACT_AUTHORSHIP_RECORD_ID,
        CONTRACT_REVIEW_RECORD_ID,
        SCHEMA_REVIEW_RECORD_ID,
        CONTRACT_SCHEMA_ACCEPTANCE_ID,
    ):
        missing_records = deepcopy(record_store)
        missing_records.pop(missing_record_id)
        with pytest.raises(CandidatePackError, match="missing external record"):
            _validate_hypothetical_external_acceptance(
                pack,
                raw_candidate_pack_bytes=raw_candidate_pack_bytes,
                contract=contract,
                fixture_contract_authority=contract_resolver,
                record_store=missing_records,
                hash_manifest=hash_manifest,
            )

    coordinated_records = deepcopy(record_store)
    foreign_subject = {
        **deepcopy(pack["upstream_contract_reference"]),
        "git_blob": "f" * 40,
        "canonical_sha256": "f" * 64,
    }
    for record_id in (
        CONTRACT_AUTHORSHIP_RECORD_ID,
        CONTRACT_REVIEW_RECORD_ID,
        SCHEMA_REVIEW_RECORD_ID,
        CONTRACT_SCHEMA_ACCEPTANCE_ID,
    ):
        coordinated_records[record_id]["contract_subject"] = deepcopy(foreign_subject)
    authorship_hash = _canonical_sha256(coordinated_records[CONTRACT_AUTHORSHIP_RECORD_ID])
    for review_id in (CONTRACT_REVIEW_RECORD_ID, SCHEMA_REVIEW_RECORD_ID):
        coordinated_records[review_id]["authorship_record_sha256"] = authorship_hash
    coordinated_records[CONTRACT_SCHEMA_ACCEPTANCE_ID]["authorship_record_sha256"] = authorship_hash
    coordinated_records[CONTRACT_SCHEMA_ACCEPTANCE_ID]["contract_review_record_sha256"] = _canonical_sha256(
        coordinated_records[CONTRACT_REVIEW_RECORD_ID]
    )
    coordinated_records[CONTRACT_SCHEMA_ACCEPTANCE_ID]["schema_review_record_sha256"] = _canonical_sha256(
        coordinated_records[SCHEMA_REVIEW_RECORD_ID]
    )
    coordinated_hashes = {record_id: _canonical_sha256(record) for record_id, record in coordinated_records.items()}
    with pytest.raises(CandidatePackError, match="accepted contract subject"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=coordinated_records,
            hash_manifest=coordinated_hashes,
        )


def test_accepted_requirement_binds_content_subject_and_exact_obligation_applicability_rows():
    """The accepted requirement must bind immutable content and every pack obligation."""
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    requirement = record_store[REQUIREMENT_RECORD_ID]
    subject = requirement["requirement_subject"]
    assert subject["assurance_requirement_id"] == requirement["assurance_requirement_id"]
    assert subject["revision"] == requirement["revision"]
    assert subject["canonical_sha256"] == _canonical_sha256(_requirement_content_preimage(requirement))

    expected_rows = {
        (lane_id, obligation["obligation_id"])
        for lane_id, lane in contract["required_pack_contract"]["lanes"].items()
        for obligation in lane["required_obligations"]
    }
    observed_rows = {(row["lane_id"], row["obligation_id"]) for row in requirement["obligation_applicability_rows"]}
    assert observed_rows == expected_rows
    assert all(row["applicability"] == "required" for row in requirement["obligation_applicability_rows"])

    missing_pack = deepcopy(pack)
    missing_records = deepcopy(record_store)
    missing_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"].pop()
    missing_raw, missing_hashes = _coordinate_all_external_hashes(missing_pack, missing_records)
    with pytest.raises(CandidatePackError, match="obligation_applicability_rows"):
        _validate_hypothetical_external_acceptance(
            missing_pack,
            raw_candidate_pack_bytes=missing_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=missing_records,
            hash_manifest=missing_hashes,
        )

    producer_only_pack = deepcopy(pack)
    producer_only_records = deepcopy(record_store)
    producer_only_row = producer_only_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0]
    producer_only_row["applicability"] = "not_applicable"
    producer_only_row["rationale"] = "producer_claimed_not_applicable"
    producer_only_row["confirming_actor_id"] = ACT_PRODUCER
    _install_applicability_confirmation(producer_only_records)
    producer_only_raw, producer_only_hashes = _coordinate_all_external_hashes(producer_only_pack, producer_only_records)
    with pytest.raises(CandidatePackError, match="applicability authority is unbound"):
        _validate_hypothetical_external_acceptance(
            producer_only_pack,
            raw_candidate_pack_bytes=producer_only_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=producer_only_records,
            hash_manifest=producer_only_hashes,
        )

    coordinated_pack = deepcopy(pack)
    coordinated_records = deepcopy(record_store)
    coordinated_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0]["applicability"] = "not_applicable"
    coordinated_raw, coordinated_hashes = _coordinate_all_external_hashes(coordinated_pack, coordinated_records)
    with pytest.raises(CandidatePackError, match="obligation_applicability_rows"):
        _validate_hypothetical_external_acceptance(
            coordinated_pack,
            raw_candidate_pack_bytes=coordinated_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=coordinated_records,
            hash_manifest=coordinated_hashes,
        )


def test_applicability_decision_times_are_bounded_by_relationship_and_acceptance():
    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    invalid_decision_times = (
        "2026-07-18T08:14:59Z",  # before relationship effective time
        "2026-07-18T08:30:01Z",  # after requirement acceptance
        "2026-07-18T12:00:01Z",  # after the validation as-of time
        "2027-07-18T08:15:00Z",  # at relationship expiry
    )
    for invalid_decision_time in invalid_decision_times:
        invalid_records = deepcopy(record_store)
        invalid_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0]["decided_at"] = invalid_decision_time
        invalid_pack = deepcopy(pack)
        invalid_raw, invalid_hashes = _coordinate_all_external_hashes(invalid_pack, invalid_records)
        with pytest.raises(CandidatePackError, match="applicability decision time"):
            _validate_hypothetical_external_acceptance(
                invalid_pack,
                raw_candidate_pack_bytes=invalid_raw,
                contract=contract,
                fixture_contract_authority=contract_resolver,
                record_store=invalid_records,
                hash_manifest=invalid_hashes,
            )


def test_independently_confirmed_not_applicable_is_reachable_and_fails_closed():
    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    confirmed_records = deepcopy(record_store)
    confirmed_row = confirmed_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0]
    confirmed_row["applicability"] = "not_applicable"
    confirmed_row["rationale"] = "not_applicable_for_the_governed_task_scope"
    _install_applicability_confirmation(confirmed_records)
    confirmed_pack = deepcopy(pack)
    confirmed_raw, confirmed_hashes = _coordinate_all_external_hashes(confirmed_pack, confirmed_records)
    _validate_hypothetical_external_acceptance(
        confirmed_pack,
        raw_candidate_pack_bytes=confirmed_raw,
        contract=contract,
        fixture_contract_authority=contract_resolver,
        record_store=confirmed_records,
        hash_manifest=confirmed_hashes,
    )

    missing_records = deepcopy(confirmed_records)
    missing_records.pop(APPLICABILITY_CONFIRMATION_ID)
    missing_pack = deepcopy(confirmed_pack)
    missing_raw, missing_hashes = _coordinate_all_external_hashes(missing_pack, missing_records)
    with pytest.raises(CandidatePackError, match="missing external record"):
        _validate_hypothetical_external_acceptance(
            missing_pack,
            raw_candidate_pack_bytes=missing_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=missing_records,
            hash_manifest=missing_hashes,
        )

    foreign_records = deepcopy(confirmed_records)
    foreign_confirmation = foreign_records[APPLICABILITY_CONFIRMATION_ID]
    foreign_confirmation["relationship_record_id"] = REVIEW_RELATIONSHIP_ID
    foreign_confirmation["applicability_decision_sha256"] = _canonical_sha256(
        {
            **_applicability_decision_preimage(
                foreign_records[REQUIREMENT_RECORD_ID],
                foreign_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0],
            ),
            "relationship_record_id": REVIEW_RELATIONSHIP_ID,
        }
    )
    foreign_row = foreign_records[REQUIREMENT_RECORD_ID]["obligation_applicability_rows"][0]
    foreign_row["confirmation_record_sha256"] = _canonical_sha256(foreign_confirmation)
    foreign_pack = deepcopy(confirmed_pack)
    foreign_raw, foreign_hashes = _coordinate_all_external_hashes(foreign_pack, foreign_records)
    with pytest.raises(CandidatePackError, match="does not bind the exact decision"):
        _validate_hypothetical_external_acceptance(
            foreign_pack,
            raw_candidate_pack_bytes=foreign_raw,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=foreign_records,
            hash_manifest=foreign_hashes,
        )


def test_c1_coordinated_full_store_forgery_cannot_supply_bodies_and_hash_oracle():
    """Caller-fabricated lifecycle bodies plus matching hashes must never be authority."""
    contract = _load_yaml(CONTRACT_PATH)
    pack = _proposed_pack(contract)
    pack, raw_candidate_pack_bytes, fabricated_store, fabricated_hashes = _external_records(pack, contract)
    fabricated_snapshot = _authority_snapshot(contract, fabricated_store, fabricated_hashes)
    parameters = inspect.signature(_validate_external_acceptance).parameters
    assert "record_store" not in parameters
    assert "hash_manifest" not in parameters

    with pytest.raises(CandidatePackError, match="trusted authority resolver"):
        _validate_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            authority_resolver=lambda _phase: fabricated_snapshot,
        )


def test_c2_bare_review_verdict_cannot_replace_canonical_requirement_and_two_key_closure():
    """Acceptance needs canonical AssuranceRequirement bytes and per-obligation W5 closure."""
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    evidence_rows = record_store[REVIEW_RECORD_ID]["obligation_evidence_rows"]
    evidence_rows[-1]["obligation_id"] = evidence_rows[0]["obligation_id"]
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)

    with pytest.raises(CandidatePackError, match="two-key evidence does not close every required obligation"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    canonical_requirement = record_store[REQUIREMENT_RECORD_ID]["canonical_requirement"]
    canonical_requirement["requested_risk"] = "R2"
    canonical_requirement["content_hash"] = _canonical_sha256(
        {key: value for key, value in canonical_requirement.items() if key != "content_hash"}
    )
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
    with pytest.raises(
        CandidatePackError, match="canonical AssuranceRequirement|invalid accepted_assurance_requirement"
    ):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
    record_store[REVIEW_RECORD_ID]["two_key_closure_sha256"] = "f" * 64
    _rehash_record(record_store, hash_manifest, REVIEW_RECORD_ID)
    record_store[OWNER_DECISION_ID]["review_record_sha256"] = hash_manifest[REVIEW_RECORD_ID]
    record_store[OWNER_DECISION_ID]["two_key_closure_sha256"] = "f" * 64
    _rehash_record(record_store, hash_manifest, OWNER_DECISION_ID)
    with pytest.raises(CandidatePackError, match="owner acceptance does not bind exact two-key evidence"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_c2_two_key_evidence_rejects_schema_valid_swapped_lane():
    """A valid obligation ID cannot close evidence under the wrong lane."""
    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    record_store[REVIEW_RECORD_ID]["obligation_evidence_rows"][0]["lane_id"] = "paper_claim"
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)

    with pytest.raises(CandidatePackError, match="two-key evidence does not close every required obligation"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_m1_distinct_actor_uuid_and_asserted_i2_fail_without_fresh_task_provenance():
    """Distinct actors and an asserted grade do not prove a separate review context."""
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture()
    )
    record_store[REVIEW_RECORD_ID]["operator_provenance"]["review_task_id"] = PRODUCER_TASK_ID
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)

    with pytest.raises(CandidatePackError, match="review task provenance"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    record_store[REVIEW_RECORD_ID]["operator_provenance"]["review_session_id"] = PRODUCER_SESSION_ID
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
    with pytest.raises(CandidatePackError, match="review task provenance"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_m2_coordinated_stale_reference_pin_fails_current_snapshot_revalidation():
    """A contract and candidate cannot jointly replace the current reference oracle."""
    contract = _eligible_contract()
    validate_topology = next(
        row
        for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]
        if row["reference_id"] == "skill/validate-topology"
    )
    validate_topology["git_blob"] = "f" * 40
    validate_topology["canonical_sha256"] = "f" * 64
    contract_resolver = _fixture_contract_authority(contract)
    _, _, contract_subject = _resolve_contract_authority(contract_resolver)
    pack = _proposed_pack(contract, contract_subject=contract_subject)
    pack, raw_candidate_pack_bytes, record_store, hash_manifest = _external_records(pack, contract)

    with pytest.raises(CandidatePackError, match="current reference snapshot"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    current_contract = _eligible_contract()
    current_contract_resolver = _fixture_contract_authority(current_contract)
    _, _, current_subject = _resolve_contract_authority(current_contract_resolver)
    current_pack = _proposed_pack(current_contract, contract_subject=current_subject)
    current_pack, current_raw, current_records, current_hashes = _external_records(current_pack, current_contract)
    stable_snapshot = _authority_snapshot(current_contract, current_records, current_hashes)
    changed_references = deepcopy(stable_snapshot.reference_subjects)
    changed_references["skill/validate-topology"]["canonical_sha256"] = "e" * 64
    changed_snapshot = _authority_snapshot(
        current_contract,
        current_records,
        current_hashes,
        snapshot_id="auth_00000000-0000-7000-8000-000000000002",
        reference_subjects=changed_references,
    )
    for snapshots in (
        (stable_snapshot, changed_snapshot),
        (stable_snapshot, stable_snapshot, changed_snapshot),
    ):
        with pytest.raises(CandidatePackError, match="authority changed during"):
            _validate_external_acceptance_with_authority(
                current_pack,
                raw_candidate_pack_bytes=current_raw,
                contract=current_contract,
                trusted_contract_resolver=current_contract_resolver,
                authority_resolver=_fixture_record_authority(
                    current_contract,
                    current_records,
                    current_hashes,
                    snapshots=snapshots,
                ),
            )


def test_review_provenance_is_required_on_every_review_record_type():
    """F-1 control: typed fresh-context provenance binds all three review records, not only the pack.

    The contract states `review_provenance_binding` at `external_acceptance_evidence` level and
    lists three `review_provenance_required_record_types`, so a review record that reuses its
    author's task or session must fail for each type independently. Before this control the
    obligation was enforced on `independent_pack_review` alone.
    """
    reused_task_and_session = (
        (CONTRACT_REVIEW_RECORD_ID, "contract", CONTRACT_AUTHOR_TASK_ID, CONTRACT_AUTHOR_SESSION_ID),
        (SCHEMA_REVIEW_RECORD_ID, "schema", CONTRACT_AUTHOR_TASK_ID, CONTRACT_AUTHOR_SESSION_ID),
        (REVIEW_RECORD_ID, "pack", PRODUCER_TASK_ID, PRODUCER_SESSION_ID),
    )
    for record_id, label, author_task_id, author_session_id in reused_task_and_session:
        for field, reused_value in (
            ("review_task_id", author_task_id),
            ("review_session_id", author_session_id),
        ):
            contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
            record_store[record_id]["operator_provenance"][field] = reused_value
            raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
            with pytest.raises(CandidatePackError, match=f"{label} review task provenance"):
                _validate_hypothetical_external_acceptance(
                    pack,
                    raw_candidate_pack_bytes=raw_candidate_pack_bytes,
                    contract=contract,
                    fixture_contract_authority=contract_resolver,
                    record_store=record_store,
                    hash_manifest=hash_manifest,
                )


def test_review_provenance_accepts_any_contract_allowed_session_family_and_agent_operator():
    """F-2 control: the operator model is provider-neutral, so a non-Codex review record is valid.

    06g authorizes the owner to select the external application; the contract records
    `session_family_selection: operator_selected` over `allowed_session_families`. A review
    produced and reviewed under `claude_standalone` must therefore validate exactly as
    `codex_standalone` does. Before this control every fixture was Codex, so a Codex-only
    narrowing in the schema and validator had no watched negative.
    """
    contract = _eligible_contract()
    operator_model = contract["required_pack_contract"]["external_acceptance_evidence"]["operator_model"]
    assert operator_model["provider_neutral"] is True
    assert operator_model["session_family_selection"] == "operator_selected"
    # Neutrality is by configuration: the contract selects a non-empty subset of the governance
    # enums. Assert the precondition this control depends on — that Claude is currently admitted —
    # rather than pinning the allowlists to an exact pair, which would make narrowing the
    # configuration look like a regression.
    assert "claude_standalone" in operator_model["allowed_session_families"]
    assert "claude_task_agent" in operator_model["allowed_agent_operator_types"]

    for session_family, operator_type in (
        ("claude_standalone", "claude_task_agent"),
        ("codex_standalone", "claude_task_agent"),
    ):
        contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
        provenance = record_store[REVIEW_RECORD_ID]["operator_provenance"]
        provenance["session_family"] = session_family
        provenance["producer_operator"]["operator_type"] = operator_type
        provenance["reviewer_operator"]["operator_type"] = operator_type
        raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_review_operator_outside_the_contract_operator_model_is_rejected():
    """F-2 control: provider-neutral is not unconstrained, at both enforcement layers.

    Two layers, two distinct controls:

    Schema layer — `agentOperatorIdentity` restricts review operators to agent types, so a
    `human_owner` review operator and a session family outside the governance enum both fail
    before the validator runs. This is what reconciles the schema with
    `human_owner_may_act_as_review_operator: false`; previously the schema admitted `human_owner`
    in this slot and only the validator objected.

    Validator layer — a value inside the governance enum but outside the *contract's* declared
    allowlist is schema-valid and can only be caught by the contract-level check. Exercised over a
    contract narrowed to `codex_standalone`, which is what makes the allowlist meaningful rather
    than decorative.
    """
    for field, value in (
        ("operator_type", "human_owner"),
        ("session_family", "gemini_standalone"),
    ):
        contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
        provenance = record_store[REVIEW_RECORD_ID]["operator_provenance"]
        if field == "operator_type":
            provenance["reviewer_operator"]["operator_type"] = value
        else:
            provenance["session_family"] = value
        raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
        with pytest.raises(CandidatePackError, match="invalid independent_pack_review record"):
            _validate_hypothetical_external_acceptance(
                pack,
                raw_candidate_pack_bytes=raw_candidate_pack_bytes,
                contract=contract,
                fixture_contract_authority=contract_resolver,
                record_store=record_store,
                hash_manifest=hash_manifest,
            )

    narrowed = _eligible_contract()
    narrowed_model = narrowed["required_pack_contract"]["external_acceptance_evidence"]["operator_model"]
    narrowed_model["allowed_session_families"] = ["codex_standalone"]
    narrowed_model["allowed_agent_operator_types"] = ["codex_task_agent"]
    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture(narrowed)
    record_store[REVIEW_RECORD_ID]["operator_provenance"]["session_family"] = "claude_standalone"
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
    with pytest.raises(CandidatePackError, match="pack review task provenance"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_review_provenance_records_must_share_one_stable_handoff_id():
    """N-3 control: `handoff_id` is bound across the review records, not merely present.

    06g section 6 requires a stable handoff identifier shared by the brief and the returned
    evidence. The contract records `handoff_binding:
    single_stable_handoff_id_shared_by_every_review_provenance_record`; before this control the
    field was schema-required and bound by nothing.

    The divergence is introduced on the pack review because the check compares all three records;
    mutating a contract- or schema-review record additionally invalidates the acceptance record's
    embedded review hashes, which fails earlier for an unrelated reason.
    """
    contract, contract_resolver, pack, _, record_store, _ = _eligible_acceptance_fixture()
    record_store[REVIEW_RECORD_ID]["operator_provenance"]["handoff_id"] = "hnd_00000000-0000-7000-8000-0000000000ff"
    raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
    with pytest.raises(CandidatePackError, match="one stable handoff identifier"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_lane_may_not_declare_a_fixture_catalogued_to_a_foreign_lane():
    """N-1 control: a lane's `exact_fixture_ids` must agree with each fixture's catalogued lane.

    The representation lane previously declared `apf_degenerate_fallback`, whose catalogue row is
    `lane_id: stochastic_null` with a stochastic target invariant. No check compared the two, so
    the cross-listing was invisible. `cross_lane` remains permitted for genuinely shared fixtures.
    """
    contract = _eligible_contract()
    lanes = contract["required_pack_contract"]["lanes"]
    fixture_rows = _rows_by_id(
        contract["required_pack_contract"]["fixtures"]["exact_fixture_rows"], "fixture_id", "fixture"
    )
    for lane_id, lane_contract in lanes.items():
        for fixture_id in lane_contract["exact_fixture_ids"]:
            assert fixture_rows[fixture_id]["lane_id"] in {lane_id, "cross_lane"}

    representation = lanes["representation"]
    assert "apf_representation_frozen_fallback" in representation["exact_fixture_ids"]
    assert "apf_degenerate_fallback" not in representation["exact_fixture_ids"]
    assert fixture_rows["apf_representation_frozen_fallback"]["lane_id"] == "representation"
    assert (
        fixture_rows["apf_representation_frozen_fallback"]["target_invariant"]
        == "invariant.representation.prohibited_refit_and_fallback"
    )

    # Negative control for the pack-side branch. The cross-listing can only exist in a contract
    # that declares it, so the mutated contract is supplied through a trusted fixture authority
    # rather than the Git-resolved one, which would reject any locally modified contract.
    cross_listed = _eligible_contract()
    cross_listed["required_pack_contract"]["lanes"]["representation"]["exact_fixture_ids"] = [
        "apf_degenerate_fallback" if fixture_id == "apf_representation_frozen_fallback" else fixture_id
        for fixture_id in cross_listed["required_pack_contract"]["lanes"]["representation"]["exact_fixture_ids"]
    ]
    cross_listed_resolver = _fixture_contract_authority(cross_listed)
    _, _, cross_listed_subject = _resolve_contract_authority(cross_listed_resolver)
    cross_listed_pack = _proposed_pack(cross_listed, contract_subject=cross_listed_subject)
    with pytest.raises(CandidatePackError, match="catalogued to a foreign lane"):
        _validate_hypothetical_proposed_pack(
            cross_listed_pack,
            contract=cross_listed,
            fixture_contract_authority=cross_listed_resolver,
            require_active_references=True,
        )


def test_declared_governed_sets_are_consumed_by_the_checks_they_name():
    """Every contract key naming a governed set must be read by the check it governs.

    Review finding F-1: `review_provenance_required_record_types`,
    `review_provenance_partial_application`, `required_executed_boundary_fixture_ids`,
    `required_distinct_pairs`, `required_temporal_order`, and the two per-kind reference counts
    were read by no executable code. The hardcoded checks beside them happened to agree, so the
    declarations described the implementation rather than governing it — editing either side
    produced no failure. Each mutation below must now fail.
    """
    # review_provenance_required_record_types has no contract-side negative control, deliberately:
    # the schema pins it to exactly the three review record types (enum plus minItems/maxItems 3),
    # so a contract edit cannot declare a fourth or drop one. The runtime equality check therefore
    # guards the *code* side — a review record type validated without being declared, or declared
    # without a provenance call site. Asserting the wiring exists is the most a contract-level test
    # can do here without relaxing a schema constraint that is doing real work.
    evidence = _eligible_contract()["required_pack_contract"]["external_acceptance_evidence"]
    assert evidence["review_provenance_partial_application"] == "prohibited"
    assert set(evidence["review_provenance_required_record_types"]) == {
        "independent_contract_review",
        "independent_schema_review",
        "independent_pack_review",
    }

    # A distinct pair the records violate.
    contract = _eligible_contract()
    # Mutate in place rather than truncating: a shorter list would fail schema validation
    # before reaching the check under test. Note the schema sets `minItems: 7` with no
    # `maxItems` — it does NOT pin the list to the eleven pairs the contract declares, so
    # four separations could be dropped with no schema signal. All eleven are load-bearing
    # (each is consumed by the distinct-pair loop below), and the accepted schema bytes are
    # frozen, so the count is bound by a test instead:
    # tests/research_system/contracts/test_tdl_private_pack_candidate.py
    # ::test_required_distinct_pairs_floor_is_bound_by_a_test_not_by_the_schema.
    contract["required_pack_contract"]["external_acceptance_evidence"]["required_distinct_pairs"][0] = [
        "contract_author",
        "contract_author",
    ]
    contract, contract_resolver, pack, raw_candidate_pack_bytes, record_store, hash_manifest = (
        _eligible_acceptance_fixture(contract)
    )
    with pytest.raises(CandidatePackError, match="required distinct pair is not distinct"):
        _validate_hypothetical_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            fixture_contract_authority=contract_resolver,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )

    # required_temporal_order likewise has no contract-side negative control: the schema pins it by
    # prefixItems to these exact four stages in this exact order, so no schema-valid contract can
    # declare a different order. As with the record types, the runtime check guards the code side —
    # a stage renamed or a timestamp wired to the wrong record. Assert the wiring, and that every
    # declared stage is resolvable, which is the part a contract-level test can establish.
    evidence = _eligible_contract()["required_pack_contract"]["external_acceptance_evidence"]
    assert evidence["required_temporal_order"] == [
        "requirement_accepted",
        "candidate_authored",
        "independent_reviewed",
        "owner_accepted",
    ]

    # The per-kind reference counts are schema `const: 6`, so they too cannot be violated from the
    # contract side. Assert them and their agreement with the actual rows; the runtime check guards
    # a reference row being added or dropped in code without the count following.
    references_contract = _eligible_contract()["required_pack_contract"]["references"]
    assert references_contract["required_contract_reference_count"] == 6
    assert references_contract["required_skill_reference_count"] == 6
    reference_rows = references_contract["exact_reference_rows"]
    assert sum(1 for row in reference_rows if row["reference_kind"] == "contract") == 6
    assert sum(1 for row in reference_rows if row["reference_kind"] == "skill") == 6

    # The three boundary-fixture copies are each pinned to the same three ids by cardinality plus a
    # closed enum, so as sets they cannot diverge from the contract side either. The runtime
    # agreement check remains as a code-side guard for the case the reviewer identified: one copy
    # was pinned as literals in a test, so widening the enum later could let two copies drift.
    contract = _eligible_contract()
    boundary = contract["required_pack_contract"]["fixture_execution_boundary"]
    declared_boundary = contract["required_pack_contract"]["external_acceptance_evidence"][
        "required_executed_boundary_fixture_ids"
    ]
    assert (
        frozenset(declared_boundary)
        == frozenset(boundary["upstream_executable_fixture_ids"])
        == frozenset(boundary["downstream_scientific_execution_fixture_ids"])
    )


def test_declared_test_surface_is_closed_not_merely_a_subset():
    """Review finding F-2: the binding was `declared <= defined`, so it accepted silent shrinkage.

    A subset assertion proves every declared name exists. It cannot detect a test function that
    exists but is undeclared — which is how this round's five remediation controls, and four
    earlier ones, sat outside the contract's enforcement surface and could have been deleted with
    no contract-level signal.
    """
    contract = _load_yaml(CONTRACT_PATH)
    bindings = contract["validation_bindings"]
    _assert_test_surface_closure(bindings)
    # The controls closing this round's findings are on the durable surface, not merely present.
    for control in (
        "test_review_provenance_is_required_on_every_review_record_type",
        "test_review_operator_outside_the_contract_operator_model_is_rejected",
        "test_lane_may_not_declare_a_fixture_catalogued_to_a_foreign_lane",
        "test_declared_governed_sets_are_consumed_by_the_checks_they_name",
        "test_declared_test_surface_is_closed_not_merely_a_subset",
    ):
        assert control in bindings["durable_test_functions"]
