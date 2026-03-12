"""
Logging configuration for CaseAI Copilot.
Provides structured logging with audit trail capabilities for AI and SQL calls.
"""
import logging
import os
from typing import Optional


def get_logger(name: str = "caseai") -> logging.Logger:
    """
    Returns a configured logger instance.

    Args:
        name: Logger name (default "caseai")

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Only configure if handlers haven't been set up yet
    if not logger.handlers:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(log_level)

        # Console handler
        handler = logging.StreamHandler()
        handler.setLevel(log_level)

        # Formatter: timestamp | level | module | message
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(module)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False

    return logger


def log_ai_call(
    model: str,
    feature: str,
    token_count: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Logs an AI API call for audit purposes.

    Args:
        model:       The model name/ID used (e.g., "claude-opus-4-6")
        feature:     The feature that triggered the call (e.g., "risk_analysis", "summary")
        token_count: Approximate token count if available
        logger:      Logger instance (uses default "caseai" logger if not provided)
    """
    _logger = logger or get_logger("caseai.audit")
    token_info = f" | tokens~{token_count}" if token_count is not None else ""
    _logger.info(f"AI_CALL | model={model} | feature={feature}{token_info}")


def log_sql_query(
    query: str,
    case_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Logs a SQL query execution for audit purposes.
    The full query is logged at DEBUG level; a truncated version at INFO.

    Args:
        query:   The SQL query string
        case_id: The case ID context for the query (if applicable)
        logger:  Logger instance (uses default "caseai.sql" logger if not provided)
    """
    _logger = logger or get_logger("caseai.sql")
    case_info = f" | case_id={case_id}" if case_id else ""
    truncated_query = query.strip().replace("\n", " ")[:120]
    _logger.info(f"SQL_QUERY{case_info} | query_preview={truncated_query!r}")
    _logger.debug(f"SQL_QUERY_FULL{case_info} | query={query!r}")
