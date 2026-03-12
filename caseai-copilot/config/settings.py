"""
Application configuration settings for CaseAI Copilot.
Loads from environment variables / .env file.
"""
import os
import warnings
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    APP_MODE: str = "demo"
    ANTHROPIC_API_KEY: str = ""
    DB_SERVER: str = ""
    DB_DATABASE: str = ""
    DB_USERNAME: str = ""
    DB_PASSWORD: str = ""
    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_AUTH: str = "windows"   # "windows" = Windows Auth | "sql" = SQL Server Auth
    LOG_LEVEL: str = "INFO"
    MODEL_NAME: str = "claude-opus-4-6"
    MAX_TOKENS: int = 4096
    # Billing tier monthly rates (USD)
    BILLING_RATE_0_30: float = 150.0
    BILLING_RATE_31_60: float = 200.0
    BILLING_RATE_61_90: float = 300.0
    BILLING_RATE_GT_90: float = 450.0


_config_instance: AppConfig = None


def get_config() -> AppConfig:
    """
    Returns the singleton AppConfig loaded from environment variables.
    Validates required fields and emits warnings for missing or invalid values.
    """
    global _config_instance
    if _config_instance is not None:
        return _config_instance

    app_mode = os.getenv("APP_MODE", "demo").strip().lower()
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    db_server = os.getenv("DB_SERVER", "").strip()
    db_database = os.getenv("DB_DATABASE", "").strip()
    db_username = os.getenv("DB_USERNAME", "").strip()
    db_password = os.getenv("DB_PASSWORD", "").strip()
    db_driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server").strip()
    db_auth = os.getenv("DB_AUTH", "windows").strip().lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    def _env_float(key: str, default: float) -> float:
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default

    billing_0_30  = _env_float("BILLING_RATE_0_30",  150.0)
    billing_31_60 = _env_float("BILLING_RATE_31_60", 200.0)
    billing_61_90 = _env_float("BILLING_RATE_61_90", 300.0)
    billing_gt_90 = _env_float("BILLING_RATE_GT_90", 450.0)

    # Validate APP_MODE
    valid_modes = ("demo", "sql")
    if app_mode not in valid_modes:
        warnings.warn(
            f"APP_MODE '{app_mode}' is invalid. Must be one of {valid_modes}. "
            f"Defaulting to 'demo'.",
            UserWarning,
        )
        app_mode = "demo"

    # Validate API key presence
    if not api_key:
        warnings.warn(
            "ANTHROPIC_API_KEY is not set. AI features will be disabled. "
            "Set ANTHROPIC_API_KEY in your .env file or environment to enable AI analysis.",
            UserWarning,
        )

    # Validate log level
    valid_log_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if log_level not in valid_log_levels:
        warnings.warn(
            f"LOG_LEVEL '{log_level}' is invalid. Defaulting to 'INFO'.",
            UserWarning,
        )
        log_level = "INFO"

    _config_instance = AppConfig(
        APP_MODE=app_mode,
        ANTHROPIC_API_KEY=api_key,
        DB_SERVER=db_server,
        DB_DATABASE=db_database,
        DB_USERNAME=db_username,
        DB_PASSWORD=db_password,
        DB_DRIVER=db_driver,
        DB_AUTH=db_auth,
        LOG_LEVEL=log_level,
        MODEL_NAME="claude-opus-4-6",
        MAX_TOKENS=4096,
        BILLING_RATE_0_30=billing_0_30,
        BILLING_RATE_31_60=billing_31_60,
        BILLING_RATE_61_90=billing_61_90,
        BILLING_RATE_GT_90=billing_gt_90,
    )

    return _config_instance


def reset_config() -> None:
    """Reset the config singleton (useful for testing)."""
    global _config_instance
    _config_instance = None
