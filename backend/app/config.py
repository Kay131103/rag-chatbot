from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"
    max_tokens: int = 1024
    chroma_path: str = "./chroma_data"
    collection_name: str = "documents"
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 4
    max_distance: float = 1.2
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
