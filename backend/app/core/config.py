from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart ShopList API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    SECRET_KEY: str = "default-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "smartlist"

    # Это поле будет автоматически загружено из .env, если оно там есть
    DATABASE_URL: str = ""

    @property
    def sync_database_url(self) -> str:
        """URL для синхронных драйверов (psycopg2)"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_database_url(self) -> str:
        """URL для асинхронных драйверов (asyncpg)"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Разрешаем лишние поля в .env (например, DATABASE_URL)


settings = Settings()