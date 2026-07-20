import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import News
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# 🗺️ КАРТА МАРШРУТИЗАЦИИ: Хэштег/Город -> ID Канала для публикации
CITY_CHANNELS = {
    "Москва": "@test_moscow_news",
    "СПб": "@test_spb_news",
    "Санкт-Петербург": "@test_spb_news",
    "Федеральные": settings.TELEGRAM_CHANNEL
}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("🤖 Бот модерации новостей запущен и готов к работе.")

@dp.callback_query(F.data.startswith("publish_"))
async def handle_publish(callback: types.CallbackQuery):
    news_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    
    try:
        news = db.query(News).filter(News.id == news_id).first()
        if not news:
            await callback.answer("❌ Новость не найдена в базе.", show_alert=True)
            return
            
        # Проверяем, есть ли город в словаре маршрутизации
        if news.city not in CITY_CHANNELS:
            await callback.answer(
                f"❌ Канал для города '{news.city}' не настроен. Добавьте его в CITY_CHANNELS.",
                show_alert=True
            )
            return
            
        target_channel = CITY_CHANNELS[news.city]
        
        # Получаем текст сообщения (ОТСТУП ИСПРАВЛЕН)
        original_text = callback.message.text or callback.message.caption

        # Удаляем хэштег из текста (всё после последнего #) (ОТСТУП ИСПРАВЛЕН)
        clean_text = re.sub(r'\s*#\w+\s*$', '', original_text).strip()

        # Отправляем очищенный текст (ОТСТУП ИСПРАВЛЕН)
        if callback.message.photo:
            await bot.send_photo(
                chat_id=target_channel,
                photo=callback.message.photo[-1].file_id,
                caption=clean_text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=target_channel,
                text=clean_text,
                parse_mode="HTML"
            )
            
        news.status = "published"
        db.commit()
        
        await callback.message.edit_text(
            f"✅ Опубликовано в: {target_channel}\n\n{clean_text}",
            reply_markup=None
        )
        await callback.answer("✅ Новость опубликована!")
        
    except Exception as e:
        logger.error(f"Ошибка при публикации: {e}") 
        await callback.answer("❌ Ошибка при публикации.", show_alert=True)
    finally:
        db.close()

@dp.callback_query(F.data.startswith("delete_"))
async def handle_delete(callback: types.CallbackQuery):
    news_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    
    try:
        news = db.query(News).filter(News.id == news_id).first()
        if news:
            news.status = "rejected"
            db.commit()
            
        await callback.message.delete()
        await callback.answer("❌ Новость удалена.")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении: {e}")
        await callback.answer("❌ Ошибка при удалении.", show_alert=True)
    finally:
        db.close()

async def main():
    logger.info("🚀 Запуск бота модерации...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
