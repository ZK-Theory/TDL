"""Control-store implementation of the pack loader's authority resolver.

The pack loader declares :class:`~research_system.assurance.pack_loader.ContentAddressedAuthorityResolver`
as the only channel through which external lifecycle records may enter acceptance: the candidate may not
supply record bodies and the caller may not supply a hash oracle. Until now the protocol had no
implementation outside test doubles, so every external record the contract requires had nowhere to live.

This resolver supplies that channel from the existing external control store. The store is the right
substrate rather than a new one because it already provides, by construction, the four properties the
contract demands of an external record:

* **Externality.** :func:`~research_system.store.layout.require_external_control_root` refuses a control
  root that is, contains, or is contained by any registered code root. A repository commit therefore
  cannot author these records — which is what makes a multi-party independence record meaningful rather
  than a producer writing both sides of its own separation claim.
* **Content addressing.** Each revision's filename is the SHA-256 of its canonical bytes, and
  :meth:`~research_system.store.objects.ObjectStore.read` re-canonicalises on every read and rejects a
  filename/content mismatch. The record's own digest is its identity.
* **Immutability.** A revision that already exists with different content raises ``ConflictError``.
* **Supersession visibility.** Resolution takes the latest revision, so a superseding revision published
  between two resolution phases changes the resolved body and the loader blocks — the contract's
  ``stale_identity_behavior: block_and_require_superseding_revision``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_system.assurance.pack_loader import AUTHORITY_RESOLUTION_PHASES
from research_system.errors import ArsError, IntegrityError
from research_system.store.identity import load_store_manifest
from research_system.store.layout import require_control_root_disjoint_from_code_roots
from research_system.store.objects import ObjectStore


#: Object kind every external assurance lifecycle record is persisted under. The record's class is
#: carried in its body and checked by the loader, which fails closed on a class mismatch, so one kind
#: is sufficient and keeps the identity registry from growing a prefix per record class.
EXTERNAL_RECORD_KIND = "assurance_record"


class ControlStoreAuthorityResolver:
    """Resolve external assurance records from an external control store.

    Attributes:
        control_root: Canonical control-store root holding the records.
        authority_root: Store-derived authority root every resolution must be bound to.
    """

    def __init__(self, control_root: Path) -> None:
        """Bind a resolver to a control store, asserting externality and deriving its authority root.

        The authority root is read from the store's own verified identity manifest rather than accepted
        from the caller, so the root supplied to :meth:`resolve` and the root the records actually live
        under are two independently obtained values that must agree.

        Disjointness from every registered code root is re-asserted here rather than trusted from
        initialization. ``initialize_control_store`` enforces it when the store is created, but
        ``load_store_manifest`` does not, so a store that was moved, or whose manifest was written
        elsewhere, would otherwise bind cleanly. Externality is the property that makes these records
        incapable of being authored by a repository commit — the whole reason this resolver is a sound
        substrate for multi-party independence records — so it is checked on every bind, against the code
        roots the manifest itself registers.

        Args:
            control_root: Canonical control-store root.

        Raises:
            ArsError: If the manifest registers no code roots, or the control root overlaps one.
            IntegrityError: If the store identity manifest is missing, malformed, or tampered.
        """
        manifest = load_store_manifest(control_root)
        code_roots = [Path(root) for root in manifest.get("code_roots", [])]
        require_control_root_disjoint_from_code_roots(code_roots, control_root)
        self.control_root = control_root
        self.authority_root = str(manifest["store_identity"])
        self._objects = ObjectStore(control_root)

    def resolve(self, *, record_id: str, record_class: str, authority_root: str, phase: str) -> Mapping[str, object]:
        """Return the current external record body for an opaque record id.

        Args:
            record_id: Opaque content-addressed record identifier.
            record_class: Required record class the caller expects.
            authority_root: Independently supplied authority root to resolve under.
            phase: One of :data:`~research_system.assurance.pack_loader.AUTHORITY_RESOLUTION_PHASES`.

        Returns:
            The resolved record body at its latest persisted revision.

        Raises:
            ArsError: If the phase is unknown, the authority root does not match the store's own, or the
                identity has no persisted revision.
            IntegrityError: If the persisted revision is missing, ambiguous, tampered, or is not a record
                body.
            ValueError: If the record identity is invalid for the external record kind.
        """
        if phase not in AUTHORITY_RESOLUTION_PHASES:
            raise ArsError(f"unknown authority resolution phase: {phase}")
        if not isinstance(record_class, str) or not record_class:
            raise ArsError("record class must be a non-empty string")
        if authority_root != self.authority_root:
            raise ArsError("authority root is not the root this control store is bound to")
        revision = self._objects.latest_revision(EXTERNAL_RECORD_KIND, record_id)
        if revision is None:
            raise ArsError(f"external record has no persisted revision: {record_id}")
        record: Any = self._objects.read(EXTERNAL_RECORD_KIND, record_id, revision)
        if not isinstance(record, dict):
            raise IntegrityError(f"external record is not a record body: {record_id}")
        return record
