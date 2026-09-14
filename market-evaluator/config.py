"""Конфигурация сервиса оценки рыночного влияния новостей."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Настройки PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "trader"
    postgres_password: str = "strongpassword"
    postgres_db: str = "crypto_news"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5

    # Настройки Binance API
    binance_base_url: str = "https://api.binance.com"
    http_timeout_seconds: float = 15.0

    # Параметры Event Study
    pre_window_hours: int = 4       # Окно ДО новости (для оценки фона и утечек)
    post_window_hours: int = 24     # Окно ПОСЛЕ новости (для оценки тренда)
    candle_interval: str = "15m"    # Таймфрейм свечей (15m, 5m, 1h)
    neutral_threshold_pct: float = 0.2  # Порог отнесения движения к нейтральному (+-0.2%)
    min_news_age_hours: float = 4.0     # Минимальный возраст новости для оценки в воркере

    # Параметры воркера
    batch_size: int = 5
    poll_interval_seconds: int = 30
    log_level: str = "INFO"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
