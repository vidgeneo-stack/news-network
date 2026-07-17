from arq import cron
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import Source, News, SourceType
from .parsers.rss_parser import RSSParser
from .ai.processor import AIProcessor
from .publishers.telegram import TelegramPublisher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем таблицы при старте, если их нет
Base.metadata.create_all(bind=engine)

async def parse_and_publish_job(ctx):
    """Фоновая задача: парсинг, AI-обработка и публикация"""
    logger.info("🔄 Запуск фоновой задачи парсинга...")
    db = SessionLocal()
    parser = RSSParser()
    ai = AIProcessor()
    publisher = TelegramPublisher()
    
    try:
        # Берем все RSS источники
        sources = db.query(Source).filter(Source.source_type == SourceType.RSS).all()
        
        for source in sources:
            logger.info(f"Парсим источник: {source.name}")
            raw_news = parser.parse_feed(source.url, limit=5)
            
            for item in raw_news:
                # Проверяем, нет ли уже такой новости
                exists = db.query(News).filter(News.source_url == item['source_url']).first()
                if exists:
                    continue
                
                # 1. Сохраняем черновик
                news = News(
                    title=item['title'],
                    content=item['content'],
                    source_url=item['source_url'],
                    image_url=item['image_url'],
                    city_id=source.city_id,
                    source_id=source.id,
                    status="draft"
                )
                db.add(news)
                db.commit()
                db.refresh(news)
                
                # 2. Обрабатываем через AI (делаем красивый рерайт)
                ai_text = ai.rewrite_for_telegram(news.title, news.content)
                
                # 3. Публикуем в Telegram
                success = publisher.publish_news(
                    title=news.title,
                    ai_text=ai_text,
                    source_url=news.source_url,
                    image_url=news.image_url
                )
                
                # 4. Меняем статус
                news.status = "published" if success else "error"
                db.commit()
                logger.info(f"✅ Обработано: {news.title[:50]}...")
                
    except Exception as e:
        logger.error(f"Критическая ошибка в воркере: {e}")
        db.rollback()
    finally:
        db.close()
        logger.info("🏁 Задача завершена.")

class WorkerSettings:
    functions = [parse_and_publish_job]
    # Запускаем автоматически каждые 30 минут (на 0-й и 30-й минуте часа)
    cron_jobs = [
        cron(parse_and_publish_job, minute=0, second=0),
        cron(parse_and_publish_job, minute=30, second=0)
    ]
    redis_host = "redis"
    redis_port = 6379
