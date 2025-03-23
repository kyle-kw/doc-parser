
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    API_KEY: str
    BASE_URL: str
    MODEL_NAME: str
    min_pixels: int = 512 * 28 * 28
    max_pixels: int = 2048 * 28 * 28

    MINERU_API_URL: str
    MINERU_API_TIMEOUT: int = 600

    class Config:
        env_file = ".env"


config = Config()
