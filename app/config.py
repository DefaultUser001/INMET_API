from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_KEY: str
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
