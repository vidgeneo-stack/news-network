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
        """Публикует новость со встроенной в текст ссылкой"""
        
        safe_title = html.escape(title)
        safe_url = html.escape(source_url)
        
        # Разбиваем текст на слова
        words = ai_text.split()
        
        # Встраиваем ссылку в последнее слово (или предпоследнее, если последнее - это частица/союз)
        if len(words) >= 2 and safe_url and safe_url != "#":
            # Берем последнее значимое слово (не предлог/союз)
            last_word = words[-1].rstrip('.,!?-;:')
            if len(last_word) > 2:  # Если слово достаточно длинное
                # Встраиваем ссылку в последнее слово
                words[-1] = f'<a href="{safe_url}">{last_word}</a>'
                final_text = ' '.join(words)
            else:
                # Если последнее слово слишком короткое, берем предпоследнее
                if len(words) >= 3:
                    words[-2] = f'<a href="{safe_url}">{words[-2].rstrip(".,!?-;:")}</a>'
                    final_text = ' '.join(words)
                else:
                    final_text = ai_text + f' <a href="{safe_url}">источник</a>'
        else:
            final_text = ai_text
        
        # Формируем пост: жирный заголовок + текст со встроенной ссылкой
        caption = f"<b> {safe_title}</b>\n\n{final_text}"
        
        payload = {
            "chat_id": settings.TELEGRAM_CHANNEL,
            "parse_mode": "HTML",
            "disable_web_page_preview": True  # Убираем дублирующее превью
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
                logger.info(f"✅ Опубликовано: {title[:50]}...")
                return True
            else:
                logger.error(f"❌ Telegram error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False
