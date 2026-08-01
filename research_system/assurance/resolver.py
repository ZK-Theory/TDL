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
from typing import Any

from research_system.assurance.pack_loader import AUTHORITY_RESOLUTION_PHASES
from research_system.assurance.external_records import (
    EXTERNAL_RECORD_KIND,
    ExternalAssuranceRecordStore,
    ExternalRecordSchemaCatalogue,
    load_complete_revision_history,
    storage_object_id,
)
from research_system.config import ControlBinding
from research_system.errors import ArsError, IntegrityError


class ControlStoreAuthorityResolver:
    """Resolve external assurance records from an external control store.

    Attributes:
        control_root: Canonical control-store root holding the records.
        authority_root: Store-derived authority root every resolution must be bound to.
    """

    def __init__(self, binding: ControlBinding) -> None:
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
            binding: A validated :class:`~research_system.config.ControlBinding`.

        Raises:
            ArsError: If the manifest registers no code roots, or the control root overlaps one.
            IntegrityError: If the store identity manifest is missing, malformed, or tampered.
        """
        if not isinstance(binding, ControlBinding):
            raise TypeError("authority resolver requires a validated ControlBinding")
        # Constructing the writer performs the binding's identity, disjointness,
        # manifest and exact-catalogue checks once; resolution then reuses its
        # read-only catalogue and the same bound control root.
        writer = ExternalAssuranceRecordStore(binding)
        self.binding = binding
        self.control_root = binding.control_root
        self.authority_root = binding.store_identity
        self._catalogue: ExternalRecordSchemaCatalogue = writer.catalogue
        self._objects = writer.objects

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
        object_id = storage_object_id(record_id)
        history = load_complete_revision_history(self._objects, EXTERNAL_RECORD_KIND, object_id)
        if not history:
            raise ArsError(f"external record has no persisted revision: {record_id}")
        row = self._catalogue.row(record_class)
        for record in history.values():
            if not isinstance(record, dict):
                raise IntegrityError(f"external record is not a record body: {record_id}")
            if record.get("record_type") != row.record_type:
                raise IntegrityError("external record revision history contains a foreign or mismatched identity")
            self._catalogue.validate(record_class, record_id, record)
        record: Any = history[max(history)]
        return record
