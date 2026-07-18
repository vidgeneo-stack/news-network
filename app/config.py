   from pydantic_settings import BaseSettings
   from functools import lru_cache

   class Settings(BaseSettings):
       DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/news_db"
       REDIS_URL: str = "redis://redis:6379"
       TELEGRAM_BOT_TOKEN: str
       TELEGRAM_CHANNEL: str
       AI_API_KEY: str
       AI_MODEL: str = "gemini-1.5-flash"
       HOST: str = "0.0.0.0"
       PORT: int = 8000
       
       class Config:
           env_file = ".env"

   @lru_cache()
   def get_settings():
       return Settings()

   settings = get_settings()
