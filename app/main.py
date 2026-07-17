from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db, engine, Base
from .models import City, Source, News, SourceType
from .worker import parse_and_publish_job
from arq.connections import create_pool
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="News Network API", version="2.0.0")

@app.get("/")
def root():
    return {"status": "ok", "message": "News Network API работает! 🚀"}

@app.post("/trigger-parse/")
async def trigger_parse(db: Session = Depends(get_db)):
    """Ручной запуск парсинга и публикации (для тестов)"""
    try:
        redis = await create_pool(host=settings.REDIS_URL.replace("redis://", ""))
        await redis.enqueue_job("parse_and_publish_job")
        return {"status": "success", "message": "Задача добавлена в очередь. Проверь логи воркера."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/")
def get_news(db: Session = Depends(get_db)):
    return db.query(News).order_by(News.id.desc()).limit(20).all()
