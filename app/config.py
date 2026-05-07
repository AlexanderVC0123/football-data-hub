import os

from dotenv import load_dotenv

from app.database.connection import ENV_PATH


load_dotenv(ENV_PATH)

DEFAULT_COMPETITIONS = ["PD", "PL", "SA", "BL1", "FL1"]


def get_bool_env(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def manual_sync_enabled() -> bool:
    default = os.getenv("APP_ENV", "development").lower() != "production"
    return get_bool_env("ENABLE_MANUAL_SYNC", default=default)
