from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "richardyoung/llama-3.2-3b-instruct-abliterated:Q4_K_M"
    OLLAMA_TRANSCRIPTION_MODEL: str = "large-v3"
    DATABASE_URL: str = "sqlite:///./classroom.db"
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    TRANSCRIPTION_CHUNK_SIZE: int = 600
    LOG_LEVEL: str = "INFO"


settings = Settings()
