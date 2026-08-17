from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================
# Project paths
# ============================================================

# config.py
#     app/
#         core/
#             config.py
#
# parents[0] = core
# parents[1] = app
# parents[2] = backend

BACKEND_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BACKEND_DIR / ".env"


# ============================================================
# Application settings
# ============================================================

class Settings(BaseSettings):

    database_url: str
    groq_api_key: str
    api_key: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ============================================================
# Global settings instance
# ============================================================

settings = Settings()