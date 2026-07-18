import httpx
import html
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        # Используем группу модерации вместо публичного канала для первичной отправки
        self.moderation_chat_id = getattr(settings, 'TELEGRAM_MODERATION_CHAT_ID', settings.TELEGRAM_CHANNEL)
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_for_moderation(self, news_id: int, title: str, ai_text: str, source_url: str, city: str, image_url: str = None) -> bool:
        """Отправляет черновик новости в группу модерации с кнопками управления"""
        
        safe_title = html.escape(title)
        safe_url = html.escape(source_url)
        safe_city = html.escape(city)
        
        # Разбиваем текст на слова (твоя рабочая логика, не тронута)
        words = ai_text.split()
        
        link_inserted = False
        if safe_url and safe_url != "#" and len(words) > 4:
            for i in [2, 3, 4]:
                if i < len(words):
                    word = words[i].strip('.,!?-;:')
                    if len(word) > 3:
                        words[i] = f'<a href="{safe_url}">{word}</a>'
                        link_inserted = True
                        break
        
        if not link_inserted and safe_url and safe_url != "#":
            words.append(f'<a href="{safe_url}">источник</a>')
        
        final_text = ' '.join(words)
        
        # Добавляем город в текст для модератора
        caption = f"<b>📰 {safe_title}</b>\n\n📍 <b>Город:</b> {safe_city}\n\n{final_text}"
        
        # Формируем Inline-клавиатуру (кнопки под постом)
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Опубликовать", "callback_data": f"publish_{news_id}"}],
                [{"text": "✏️ Редактировать", "callback_data": f"edit_{news_id}"}],
                [{"text": "❌ Удалить", "callback_data": f"delete_{news_id}"}]
            ]
        }
        
        payload = {
            "chat_id": self.moderation_chat_id,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": keyboard  # <-- ДОБАВЛЕНО: кнопки
        }

        try:
            if image_url and image_url.startswith("http"):
                payload["photo"] = image_url
                payload["caption"] = caption
                response = httpx.post(f"{self.base_url}/sendPhoto", json=payload, timeout=15.0)
            else:
                payload["text"] = caption
                response = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=15.0)
            
            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Отправлено на модерацию (ID: {news_id}): {title[:50]}...")
                return True
            else:
                logger.error(f"❌ Telegram error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception при отправке на модерацию: {e}")
            return False
