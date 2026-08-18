from pydantic_settings import BaseSettings, SettingsConfigDict

class UserAccess(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config=SettingsConfigDict(
        env_file=".env"
    )

user_access = UserAccess()
