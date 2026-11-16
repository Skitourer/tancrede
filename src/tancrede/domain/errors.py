"""Error hierarchy (SPEC §7)."""


class TancredeError(Exception):
    """Base class for every error raised by Tancrède.

    Messages must never contain source, prompt or answer text: they may end up
    in `real` logs (SPEC §11).
    """


class ConfigError(TancredeError):
    """Invalid or missing configuration."""


class ProfileViolation(TancredeError):
    """A `dev` / `real` isolation rule was broken (SPEC §11)."""


class ExcludedByClassification(TancredeError):
    """Content carries an excluded label (SPEC §5)."""


class StaleVersion(TancredeError):
    """The target of a proposal changed before execution (R3)."""


class SourceUnavailable(TancredeError):
    """A source cannot be read."""


class ModelUnavailable(TancredeError):
    """No gateway could serve the request."""


class ModeViolation(TancredeError):
    """An `enclave` guardrail was broken (SPEC §4)."""
