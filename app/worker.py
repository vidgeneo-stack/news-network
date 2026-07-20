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
            logger.info(f"📡 Парсим источник: {source.name}")
            raw_news = parser.parse_feed(source.url, limit=15) # Вернул 15, 50 могут дать таймаут
            
            logger.info(f"📦 Всего получено новостей от парсера: {len(raw_news)}")
            
            processed_count = 0
            skipped_count = 0
            
            for item in raw_news:
                item_url = item.get('source_url') or item.get('link') or item.get('url') or item.get('href', 'unknown_url')
                item_title = item.get('title', 'Без заголовка')
                item_content = item.get('content', item.get('description', ''))
                item_image = item.get('image_url')
                
                logger.info(f"🔍 Проверяем: {item_title[:40]}... | URL: {item_url}")
                
                exists = db.query(News).filter(News.source_url == item_url).first()
                if exists:
                    logger.info(f"⏭️ Пропускаем (уже в базе)")
                    skipped_count += 1
                    continue
                
                logger.info(f"🚀 Новость новая! Отправляем в ИИ...")
                
                ai_result = ai.rewrite_for_telegram(item_title, item_content)
                ai_text = ai_result["text"]
                city = ai_result["city"]
                
                news = News(
                    title=item_title,
                    content=ai_text,
                    source_url=item_url,
                    source_id=source.id,
                    image_url=item_image,
                    status="draft"
                )
                db.add(news)
                db.commit()
                db.refresh(news)
                
                success = publisher.send_for_moderation(
                    news_id=news.id,
                    title=news.title,
                    ai_text=news.content,
                    source_url=news.source_url,
                    city=city,
                    image_url=news.image_url
                )
                
                if success:
                    logger.info(f"✅ Отправлено на модерацию (ID: {news.id})")
                    processed_count += 1
                else:
                    logger.error(f"❌ Ошибка отправки (ID: {news.id})")
                    news.status = "error"
                    db.commit()
            
            logger.info(f"📊 Итог: Обработано {processed_count}, Пропущено {skipped_count}")
                
    except Exception as e:
        logger.error(f"💥 Критическая ошибка в воркере: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        logger.info("🏁 Задача завершена.")

class WorkerSettings:
    functions = [parse_and_publish_job]
    cron_jobs = [
        cron(parse_and_publish_job, minute=0, second=0),
        cron(parse_and_publish_job, minute=10, second=0),
        cron(parse_and_publish_job, minute=20, second=0),
        cron(parse_and_publish_job, minute=30, second=0),
        cron(parse_and_publish_job, minute=40, second=0),
        cron(parse_and_publish_job, minute=50, second=0)
    ]
    redis_settings = RedisSettings(host='redis', port=6379)
