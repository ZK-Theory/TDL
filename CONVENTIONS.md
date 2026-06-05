# CONVENTIONS

## ALWAYS

- Contract enforcement is default-on: every contract invariant carries exactly one of `expression` or `enforced_by`; every `binding.must_assert` lettered clause is claim-to-assertion-covered by the binding test and local validators it calls; every schema `required_key` type/bound is enforced, not merely present. Provenance contracts grandfather pre-existing immutable outputs only through explicit `legacy_exempt` entries and never backfill inferred provenance into historical result JSONs.
