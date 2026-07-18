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

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        # Используем XML-теги, чтобы ИИ не путал инструкцию с исходным текстом
        prompt = f"""<task>
Ты — профессиональный новостной редактор Telegram-канала. Сделай качественный, компактный рерайт новости своими словами.
</task>

<rules>
1. Напиши связный, грамотный текст, передающий главную суть. Объем не ограничен, пиши столько, сколько нужно для полноты.
2. Начинай текст строго с ЗАГЛАВНОЙ буквы.
3. Текст должен быть ПОЛНОСТЬЮ завершенным. Последнее предложение должно заканчиваться СТРОГО ТОЧКОЙ. 
4. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать многоточие (...) или обрывать мысль на полуслове.
5. Запрещены клише: "по словам", "как сообщает", "отмечается", "по данным".
6. Сохрани ключевые факты: имена, цифры, названия мест.
</rules>

<source_text>
Заголовок: {title}
Текст: {content[:2000]}
</source_text>

Напиши ТОЛЬКО итоговый текст рерайта. Без вступлений, без пояснений, без кавычек.
"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 800} # Чуть снизили temperature для большей строгости
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            with httpx.Client(proxy=self.proxy, timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                rewritten = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                rewritten = self._safe_fix_spacing(rewritten)
                rewritten = self._ensure_complete_sentence(rewritten)
                return rewritten
                
        except Exception as e:
            logger.error(f"Gemini HTTP ошибка через прокси: {e}")
            return f"[Ошибка ИИ: не удалось сгенерировать текст]"
    
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
