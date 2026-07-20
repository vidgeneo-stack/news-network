from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import Source, News, SourceType
from .parsers.rss_parser import RSSParser
from .ai.processor import AIProcessor
from .publishers.telegram import TelegramPublisher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

async def parse_and_publish_job(ctx):
    logger.info("🔄 Запуск фоновой задачи парсинга...")
    db = SessionLocal()
    parser = RSSParser()
    ai = AIProcessor()
    publisher = TelegramPublisher()
    
    try:
        sources = db.query(Source).filter(Source.source_type == SourceType.RSS).all()
        
        for source in sources:
            logger.info(f"Парсим источник: {source.name}")
            raw_news = parser.parse_feed(source.url, limit=50)
            
            for item in raw_news:
                # Безопасное получение данных из парсера
                item_url = item.get('link') or item.get('url') or item.get('href', 'unknown_url')
                item_title = item.get('title', 'Без заголовка')
                item_content = item.get('content', item.get('description', ''))
                item_image = item.get('image_url')
                
                exists = db.query(News).filter(News.source_url == item_url).first()
                if exists:
                    continue
                
                # 1. Получаем рерайт и город от ИИ
                ai_result = ai.rewrite_for_telegram(item_title, item_content)
                ai_text = ai_result["text"]
                city = ai_result["city"]
                
                # 2. Создаем запись в БД (ИСПРАВЛЕНО: source_id вместо source_name)
                news = News(
                    title=item_title,
                    content=ai_text,
                    source_url=item_url,
                    source_id=source.id,  # <-- ИСПРАВЛЕНО
                    image_url=item_image,
                    status="draft"
                )
                db.add(news)
                db.commit()
                db.refresh(news)
                
                # 3. Отправляем на модерацию (передаем city как текст для сообщения)
                success = publisher.send_for_moderation(
                    news_id=news.id,
                    title=news.title,
                    ai_text=news.content,
                    source_url=news.source_url,
                    city=city,
                    image_url=news.image_url
                )
                
                if success:
                    logger.info(f"✅ Отправлено на модерацию (ID: {news.id}): {news.title[:50]}...")
                else:
                    logger.error(f"❌ Ошибка отправки на модерацию (ID: {news.id})")
                    news.status = "error"
                    db.commit()
                
    except Exception as e:
        logger.error(f"Критическая ошибка в воркере: {e}")
        db.rollback()
    finally:
        db.close()
        logger.info("🏁 Задача завершена.")

class WorkerSettings:
    functions = [parse_and_publish_job]
    cron_jobs = [
        cron(parse_and_publish_job, minute=0, second=0),
        cron(parse_and_publish_job, minute=30, second=0)
    ]
    redis_settings = RedisSettings(host='redis', port=6379)
