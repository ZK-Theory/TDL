# Scout Review Playbook

Use this when no skill wrapper is available and a worker must triage a Scout
inbox note into Discovery backlog candidates.

## Inputs

- `vault/00-Meta/Discovery/_inbox/YYYY-Www.md`
- `scout/watchlist.yaml`
- Existing `vault/00-Meta/Discovery/_backlog.md`, if present

## Procedure

1. Read every hit in `_inbox/YYYY-Www.md`; do not trust stream tags blindly.
2. Cluster near-duplicates and keep the strongest representative.
3. Drop noise where the hit is not actually TDA-as-method, has no usable
   abstract, or is only a broad framework without a falsifiable topological
   claim.
4. Keep hits that use persistent homology, persistence diagrams, Mapper,
   persistent Laplacians, topological deep learning, or adjacent methods in a way
   relevant to longitudinal/panel social data, finance, spatial inequality, or
   the TDA methods frontier.
5. Write a `## Triage` table back into the inbox note.
6. Add only the strongest actionable candidates to `_backlog.md` with
   `state: triaged` and `next: /assay`.

## Outputs

- Updated inbox note with a `## Triage` table.
- Updated `vault/00-Meta/Discovery/_backlog.md` for PROMOTE-to-Assay candidates.

## Validation

- Every hit has a KEEP/DROP reason in the triage table.
- Backlog entries are `state: triaged`, not assayed or spiked.
- The playbook performs no Axis 1/2/3 scoring; that belongs to Assay.
