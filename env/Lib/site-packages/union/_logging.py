"""Configure loggers for remote or local execution."""

import logging
import os

# Configure logging for local or remote execution
LOGGING_REMOTE_ENV_VAR = "UNION_SDK_REMOTE_LOGGING_LEVEL"
LOGGING_ENV_VAR = "UNION_SDK_LOGGING_LEVEL"


def _init_global_loggers():
    """Initialize global loggers."""
    logger_configured = _init_logger(LOGGING_ENV_VAR)

    if logger_configured:
        # Logger is already configured, do not need to create another handler
        return

    if "FLYTE_INTERNAL_EXECUTION_ID" in os.environ:
        _init_logger(LOGGING_REMOTE_ENV_VAR)


def _init_logger(env_var: str) -> bool:
    """Return True if logger is configured."""
    logging_level = os.getenv(env_var)
    if logging_level is None:
        return False

    logger = logging.getLogger("union")
    if logger.handlers:
        # There are already handlers, no need to configure it
        return True

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt="[%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(int(logging_level))

    return True
