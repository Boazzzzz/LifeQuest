class LifeQuestError(Exception):
    """Base class for application-level failures."""


class LifeQuestValidationError(LifeQuestError, ValueError):
    """Raised when domain input is structurally valid but invalid for LifeQuest."""


class NotFoundError(LifeQuestError, ValueError):
    """Raised when a requested LifeQuest resource cannot be found."""


class ConflictError(LifeQuestError, ValueError):
    """Raised when a requested write conflicts with existing state."""


class ExternalServiceError(LifeQuestError, RuntimeError):
    """Raised when an optional external integration fails."""


class ConfigurationError(LifeQuestError, RuntimeError):
    """Raised when LifeQuest cannot run because required configuration is missing."""
