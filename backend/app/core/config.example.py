from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite:///./dev.db"
    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET: str = "change-me-with-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:8000,http://127.0.0.1:8000"

    # Agente de recomendaciones: gateway OpenAI-compatible. Sin AGENTE_API_KEY el
    # pipeline corre en modo catálogo (determinístico, sin LLM) y no rompe el flujo.
    AGENTE_BASE_URL: str = "https://opencode.ai/inference/go/v1"
    AGENTE_API_KEY: str = ""
    AGENTE_MODELO: str = "deepseek-v4.1-flash"
    AGENTE_TIMEOUT_S: int = 45
    AGENTE_REINTENTOS: int = 1

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
