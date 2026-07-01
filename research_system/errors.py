"""Typed errors for the Agentic Research System."""


class ArsError(Exception):
    """Base error for fail-closed ARS operations."""


class ConfigurationError(ArsError):
    """Raised when tracked ARS configuration is invalid."""

class SchemaError(ArsError):
    """Raised when an ARS schema or validated value is invalid."""
