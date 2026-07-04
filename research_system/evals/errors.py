"""Closed failure classes for deterministic evaluation handling."""


class EvaluationError(Exception):
    """Base class for evaluation failures that must remain visible."""


class FixtureDefinitionError(EvaluationError):
    """The immutable fixture or its policy is invalid and must quarantine."""


class MissingEvidence(EvaluationError):
    """Required normalized evidence is absent from an evaluation run."""


class UnableToGrade(MissingEvidence):
    """The evidence cannot support the required grader judgment."""
