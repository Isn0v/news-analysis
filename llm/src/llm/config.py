"""Конфигурация сервиса анализа сентимента через Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Настройки PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "trader"
    postgres_password: str = "strongpassword"
    postgres_db: str = "crypto_news"

    # Настройки LLM-провайдера (по умолчанию локальный DeepSeek-R1 через Ollama)
    llm_api_key: str = "ollama"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "deepseek-r1:14b"

    # Параметры воркера
    batch_size: int = 5
    poll_interval_seconds: int = 10
    max_content_chars: int = 6000  # Ограничение длины статьи для гарантированного вмещения в контекст
    max_concurrent_requests: int = 2  # Параллельных запросов к LLM

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
