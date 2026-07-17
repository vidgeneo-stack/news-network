import httpx
import html
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.channel = settings.TELEGRAM_CHANNEL
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def publish_news(self, title: str, ai_text: str, source_url: str, image_url: str = None) -> bool:
        """Публикует новость, встраивая ссылку в одно из первых слов текста"""
        
        safe_title = html.escape(title)
        safe_url = html.escape(source_url)
        
        # Разбиваем текст на слова
        words = ai_text.split()
        
        # Ищем подходящее слово для встраивания ссылки (3-е или 4-е слово, длина > 3 букв)
        link_inserted = False
        if safe_url and safe_url != "#" and len(words) > 4:
            # Пробуем вставить в 3-е или 4-е слово (обычно там глагол или важное существительное)
            for i in [2, 3, 4]:
                if i < len(words):
                    word = words[i].strip('.,!?-;:')
                    if len(word) > 3:  # Если слово достаточно длинное
                        words[i] = f'<a href="{safe_url}">{word}</a>'
                        link_inserted = True
                        break
        
        # Если не удалось вставить в начало, добавляем в конец
        if not link_inserted and safe_url and safe_url != "#":
            words.append(f'<a href="{safe_url}">источник</a>')
        
        final_text = ' '.join(words)
        
        # Формируем пост: жирный заголовок + текст со встроенной ссылкой
        caption = f"<b>📰 {safe_title}</b>\n\n{final_text}"
        
        payload = {
            "chat_id": self.channel,
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
