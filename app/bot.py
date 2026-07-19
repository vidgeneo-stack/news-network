import logging
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
# ЗАМЕНИ эти @каналы на реальные ID твоих каналов (вида -1001234567890)
CITY_CHANNELS = {
    "Москва": "@test_moscow_news",       # Или числовой ID канала Москвы
    "СПб": "@test_spb_news",             # Или числовой ID канала СПб
    "Санкт-Петербург": "@test_spb_news", # На всякий случай
    "Федеральные": settings.TELEGRAM_CHANNEL # Твой основной канал по умолчанию
}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("🤖 Бот модерации новостей запущен и готов к работе.")

@dp.callback_query(F.data.startswith("publish_"))
async def handle_publish(callback: types.CallbackQuery):
    news_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    
    try:
        # 1. Находим новость в базе
        news = db.query(News).filter(News.id == news_id).first()
        if not news:
            await callback.answer("❌ Новость не найдена в базе.", show_alert=True)
            return

        # 2. Определяем целевой канал на основе города новости
        target_channel = CITY_CHANNELS.get(news.city, CITY_CHANNELS["Федеральные"])
        
        # 3. Пересылаем сообщение из группы модерации в целевой канал
        # (Мы пересылаем оригинальное сообщение, чтобы сохранить текст, картинку и форматирование)
        await bot.forward_message(
            chat_id=target_channel,
            from_chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
        
        # 4. Обновляем статус в базе
        news.status = "published"
        db.commit()
        
        # 5. Уведомляем модератора и удаляем кнопки (или меняем текст)
        await callback.message.edit_text(
            f"✅ Опубликовано в: {target_channel}\n\n{callback.message.text}",
            reply_markup=None # Убираем кнопки после публикации
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
        # 1. Находим новость и меняем статус
        news = db.query(News).filter(News.id == news_id).first()
        if news:
            news.status = "rejected"
            db.commit()
            
        # 2. Удаляем сообщение из группы модерации
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
