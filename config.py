from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path
from typing import Literal

class Settings(BaseSettings):
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DATABASE_URL:str
    BASE_URL:str
    TEST_DATABASE_URL:str | None = None
    MAX_BODY_BYTES: int = 65536
    @field_validator("BASE_URL")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    model_config=SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        extra="ignore",
        env_file_encoding="utf-8"
    )

settings = Settings()


    
