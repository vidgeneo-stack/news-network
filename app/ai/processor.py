import httpx
import logging
import re
from ..config import settings

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        self.proxy = settings.PROXY_URL
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def rewrite_for_telegram(self, title: str, content: str) -> dict:
        # ИСПРАВЛЕНО: Добавлен правильный отступ
        prompt = f"""<task>
Ты — редактор криминально-новостного Telegram-канала в стиле "живой рассказчик". Сделай компактный рерайт новости.
</task>

<rules>
1. СТИЛЬ: Живой, динамичный, с легким криминальным оттенком. Используй короткие рубленые фразы.
2. ЭМОДЗИ: В начале поставь ОДИН тематический эмодзи (⚖️, 🚔, 💀, 🌍, 🏥).
3. КАВЫЧКИ: Строго сохраняй русские кавычки-«ёлочки» (« ») для названий, статей, терминов.
4. ЗАВЕРШЕННОСТЬ: Последнее предложение заканчивается ТОЧКОЙ. Многоточия запрещены.
5. ФАКТЫ: Сохрани все ключевые факты: имена, должности, цифры, места.
6. ГОРОД: Определи, о каком городе/регионе идет речь. Если федеральная — пиши "Федеральные".
7. ХЭШТЕГ: В самом конце текста добавь хэштег города: #Москва, #СПб, #Казань, #Федеральные и т.д.
</rules>

<source_text>
Заголовок: {title}
Текст: {content[:2500]}
</source_text>

Напиши ТОЛЬКО итоговый текст рерайта с хэштегом в конце. Без вступлений, без пояснений.
"""
        # ИСПРАВЛЕНО: Удален мусорный комментарий, который был здесь
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"enabled": True} # Оставил как ты просил
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/vidgeneo-stack/news-network",
            "X-Title": "News Network Bot"
        }
        
        try:
            with httpx.Client(proxy=self.proxy, timeout=30.0) as client:
                response = client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                message = data['choices'][0]['message']
                rewritten = message.get('content', '').strip()
                
                # ИСПРАВЛЕНО: Извлекаем город, чтобы вернуть словарь, как ожидает worker.py
                city = self._extract_city_from_hashtag(rewritten)
                
                rewritten = self._safe_fix_spacing(rewritten)
                rewritten = self._ensure_complete_sentence(rewritten)
                
                # ИСПРАВЛЕНО: Возвращаем словарь, а не строку
                return {"text": rewritten, "city": city}
                
        except Exception as e:
            logger.error(f"OpenRouter ошибка: {e}")
            # ИСПРАВЛЕНО: Возвращаем словарь даже при ошибке, чтобы бот не упал
            return {"text": "Не удалось сгенерировать рерайт для этой новости.", "city": "Федеральные"}

    def _extract_city_from_hashtag(self, text: str) -> str:
        match = re.search(r'#(\w+)$', text)
        if match:
            hashtag = match.group(1)
            city_map = {
                "Москва": "Москва", "СПб": "Санкт-Петербург", 
                "Казань": "Казань", "Федеральные": "Федеральные"
            }
            return city_map.get(hashtag, "Федеральные")
        return "Федеральные"
    
    def _safe_fix_spacing(self, text: str) -> str:
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        text = re.sub(r'([а-яё])([A-ZА-ЯЁ])', r'\1 \2', text)
        text = re.sub(r'([a-z])([А-Я])', r'\1 \2', text)
        text = re.sub(r'([А-Яа-яA-Za-z])\(', r'\1 (', text)
        text = re.sub(r'\)([А-Яа-яA-Za-z])', r') \1', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _ensure_complete_sentence(self, text: str) -> str:
        if not text:
            return text
        if text.endswith('...'):
            text = text[:-3] + '.'
        elif not text[-1] in '.!?':
            words = text.split()
            if len(words) > 1:
                if len(words[-1]) <= 3:
                    text = ' '.join(words[:-1]) + '.'
                else:
                    text = text.rstrip('.,!?') + '.'
        return text
