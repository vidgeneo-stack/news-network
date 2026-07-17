from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/news_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL: str
    
    # Groq AI
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama3-8b-8192"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
