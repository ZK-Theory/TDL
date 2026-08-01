# WP6.4 restored-store binding r2 exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, adversarial, read-only
- Reviewed subject: `523a354ada0ccbdd6c459f4e106c30443fb89c9f`
- Direct parent: `d46535c081eada7e6efa67ecfa6d48f027aeff00`
- Tree: `c7366060204d31fad7501f104abf623e0ed076cf`
- Corrective delta: 9 paths
- Verdict: `rework_required`
- Findings: 1 Critical, 3 Major, 0 Minor

## Executive disposition

The subject preserves the working authority, replay, reopen, revocation, and
race controls from the prior correction. It also leaves the protected
`VerifyRestore`, grant, administrator, and additive-action bytes unchanged.
Those are meaningful retained positives.

The exact subject remains unsafe to integrate. Its trusted-root identity is
self-anchored, so a coordinated substitution of source and target manifests,
code roots, and schema roots can pass the public CLI. It can also leave a bound
manifest without published configuration, report success or a pending result
after mutating state when durability is unsupported, and finalize a restore
bind before later command conflict or validation fails. The subject is
quarantined and is not PR- or merge-authorized; KAN-57, WP6.4, and Gate 6
remain open.

## Exact identity and retained positive controls

The reviewer bound the verdict to the subject, direct parent, tree, and exact
nine-path delta above. The reviewed positive controls covered:

- authority enforcement;
- replay and reopen behavior;
- grant revocation;
- concurrent-race handling; and
- unchanged protected `VerifyRestore`, grant, administrator, and additive
  authority-action bytes.

These controls do not establish closure of the findings below. No broader test
result or evidence is inferred here.

## C-01 - trusted root identity is self-anchored

The expected source and target root identities are derived from the same
manifests and code/schema roots they are meant to authenticate. A coordinated
substitution of the source and target manifests together with their code and
schema roots therefore passed the public CLI instead of failing closed.

The correction must obtain the expected roots from an independent approved
authority, bind them to the operation, and recheck both source and target under
the final locks immediately before commit. A substituted manifest, code root,
schema root, or joint substitution must leave the target unchanged.

## M-01 - late configuration publication can strand a bound target

The target manifest is replaced before configuration/output publication. A
later publication failure can therefore leave the store durably bound while
the required configuration is absent, with no atomic successful outcome.

All fallible output, collision, and configuration checks must complete before
manifest replacement. If publication cannot be included in one atomic commit,
the implementation needs a narrow durable journal that records the exact
committed state and supports deterministic completion or recovery without
misreporting an unchanged target.

## M-02 - unsupported durability is rejected too late

When the platform cannot provide the required durability guarantee, the
operation can return success or a pending outcome only after mutating the
target. Unsupported durability is a precondition failure, not permission to
bind first and qualify the result afterward.

The correction must detect and reject unsupported durability before any bind,
manifest replacement, configuration publication, or evidence mutation. Every
such rejection must leave all target state unchanged.

## M-03 - command validation can fail after restore finalization

`CommandService` can finalize the restore bind before completing later command
conflict and command-validation checks. It can consequently return a conflict
while the manifest and restore evidence already record a successful bind.

All command identity, idempotency, conflict, payload, authorization, collision,
and other fallible validation must precede restore finalization. Alternatively,
the manifest, evidence, and command result must participate in one atomic
commit with a narrow durable recovery record. A rejected command must not
change the bound manifest or evidence.

## Required bounded correction

The next exact subject must:

1. consume independently approved expected code, schema, source, and target
   roots and revalidate them under the final locks;
2. preflight every fallible command, collision, output, configuration, and
   durability check before mutation;
3. commit manifest, evidence, configuration, and command outcome atomically,
   or use a narrow durable journal with deterministic recovery semantics;
4. prove that every rejection leaves the target manifest, evidence, and
   outputs unchanged; and
5. preserve the passing authority, replay, reopen, revocation, race, and
   protected-byte controls.

A fresh independent exact-subject review is required before integration or a
PR. No provider, credential, live research, assurance-pack acceptance, or Gate
6 dispatch action belongs in this correction.
