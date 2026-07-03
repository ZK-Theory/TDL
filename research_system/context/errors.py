"""Typed context-compilation failures."""

from research_system.errors import ArsError


class ContextBudgetExceeded(ArsError):
    """Raised when either context token gate rejects a candidate."""
