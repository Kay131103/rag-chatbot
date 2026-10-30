from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["anthropic", "gemini"] = "anthropic"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    claude_model: str = "claude-sonnet-5-5"
    max_tokens: int = 1024
    chroma_path: str = "./chroma_data"
    collection_name: str = "documents"
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 4
    max_distance: float = 1.2
    max_upload_mb: int = 25
    app_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def llm_configured(self) -> bool:
        key = self.anthropic_api_key if self.llm_provider == "anthropic" else self.gemini_api_key
        return bool(key)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
