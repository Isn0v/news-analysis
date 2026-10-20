"""Конфигурация сервиса анализа сентимента через Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
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

    # Настройки LLM-провайдера (Ollama / Groq / DeepSeek / OpenAI)
    groq_api_key: str = ""
    llm_api_key: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "deepseek-r1:14b"
    llm_temperature: float = 0.1
    llm_num_ctx: int = 16384
    llm_timeout: float = 120.0
    llm_max_retries: int = 3

    # Параметры распределенной очереди и воркера
    worker_id: str = ""
    lock_timeout_minutes: int = 5
    batch_size: int = 3
    poll_interval_seconds: int = 10
    error_retry_delay_seconds: int = 5
    max_content_chars: int = 4000
    max_concurrent_requests: int = 2
    log_level: str = "INFO"

    def model_post_init(self, __context):
        # Если worker_id не задан явно через WORKER_ID, генерируем читаемый ID
        if not self.worker_id:
            import socket
            import uuid
            hostname = socket.gethostname()[:8]
            unique_hex = uuid.uuid4().hex[:4]
            self.worker_id = f"worker-{hostname}-{unique_hex}"

        # Если передан GROQ_API_KEY, используем его как основной токен
        if self.groq_api_key and self.llm_api_key == "ollama":
            self.llm_api_key = self.groq_api_key

        # Автоматическая настройка для токенов Groq (начинаются с gsk_)
        if self.llm_api_key.startswith("gsk_"):
            if "11434" in self.llm_base_url or "127.0.0.1" in self.llm_base_url:
                self.llm_base_url = "https://api.groq.com/openai/v1"
            if self.llm_model == "deepseek-r1:14b":
                self.llm_model = "llama-3.3-70b-versatile"

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
