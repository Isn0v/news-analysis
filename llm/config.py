"""Конфигурация сервиса анализа сентимента через Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Настройки PostgreSQL (учетные данные и пул)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "trader"
    postgres_password: str = ""  # Указывается строго через .env или переменные среды
    postgres_db: str = "crypto_news"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    # Настройки LLM-провайдера (Ollama / DeepSeek / OpenAI)
    llm_api_key: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "deepseek-r1:14b"
    llm_temperature: float = 0.1
    llm_num_ctx: int = 16384
    llm_timeout: float = 120.0
    llm_max_retries: int = 3

    # Параметры воркера
    batch_size: int = 3
    poll_interval_seconds: int = 10
    error_retry_delay_seconds: int = 5
    max_content_chars: int = 4000
    max_concurrent_requests: int = 2
    log_level: str = "INFO"

    @property
    def postgres_dsn(self) -> str:
        if not self.postgres_password:
            raise ValueError(
                "Переменная POSTGRES_PASSWORD не задана! "
                "Укажите пароль в файле .env или через переменную окружения."
            )
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
