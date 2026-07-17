import httpx
import html
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.channel = settings.TELEGRAM_CHANNEL
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def publish_news(self, title: str, ai_text: str, source_url: str, image_url: str = None) -> bool:
        """Публикует новость в Telegram канал"""
        
        # 1. Формируем красивый текст
        safe_title = html.escape(title)
        safe_text = html.escape(ai_text)
        safe_url = html.escape(source_url)
        
        # Формат: Жирный заголовок + текст от AI + ссылка
        caption = f"<b>📰 {safe_title}</b>\n\n{safe_text}\n\n<a href=\"{safe_url}\">Читать полностью на сайте</a>"
        
        payload = {
            "chat_id": self.channel,
            "parse_mode": "HTML",
            "disable_web_page_preview": True  # ОТКЛЮЧАЕМ надоедливое превью-дублирование!
        }

        try:
            # Если есть картинка, отправляем фото с текстом
            if image_url and image_url.startswith("http"):
                payload["photo"] = image_url
                payload["caption"] = caption
                response = httpx.post(f"{self.base_url}/sendPhoto", json=payload, timeout=15.0)
            else:
                # Иначе просто текст
                payload["text"] = caption
                response = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=15.0)
            
            result = response.json()
            if result.get("ok"):
                logger.info(f"Успешно опубликовано: {title}")
                return True
            else:
                logger.error(f"Ошибка Telegram: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Исключение при отправке в Telegram: {e}")
            return False
