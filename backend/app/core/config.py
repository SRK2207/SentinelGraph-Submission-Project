from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3-flash-preview", alias="GEMINI_MODEL")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    max_agent_iterations: int = Field(default=8, alias="MAX_AGENT_ITERATIONS")
    max_tool_calls: int = Field(default=12, alias="MAX_TOOL_CALLS")

    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR / ".env"), str(BASE_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip() and not self.gemini_api_key.startswith("your_"))


settings = Settings()
