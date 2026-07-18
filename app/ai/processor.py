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
        prompt = f"""
Ты — профессиональный новостной редактор Telegram-канала. Сделай качественный, компактный РЕРАЙТ новости своими словами.

ПРИМЕР РЕРАЙТА:
Оригинал: "Президент России провел встречу с министрами правительства. На совещании обсуждались вопросы экономического развития страны. По словам пресс-секретаря, встреча длилась три часа."
Рерайт: "Глава государства встретился с членами кабинета министров. Главной темой переговоров стала экономика. Переговоры продолжались три часа."

ПРАВИЛА (СТРОГО):
1. ПЕРЕФРАЗИРУЙ текст полностью своими словами. Не копируй оригинальные фразы!
2. Сделай новость КОМПАКТНОЙ и ёмкой, убери воду, оставь только главную суть. (Количество предложений не ограничено, пиши столько, сколько нужно для связного текста).
3. Начинай текст строго с ЗАГЛАВНОЙ буквы. Не вырывай фрагменты из середины оригинала!
4. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать многоточие (...) в конце текста или обрывать мысль.
5. Последнее предложение должно быть ПОЛНЫМ, логически завершенным и заканчиваться СТРОГО ТОЧКОЙ.
6. ЗАПРЕЩЕНЫ журналистские клише: "по словам", "как сообщает", "отмечается", "по данным", "источник".
7. Сохрани ВСЕ ключевые факты: имена, даты, цифры, названия мест.

Заголовок: {title}
Оригинал: {content[:2500]}

Напиши ТОЛЬКО готовый рерайт (без кавычек, пояснений и слова "источник"):
"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}
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
        # Если ИИ всё же поставил многоточие, заменяем его на точку
        if text.endswith('...'):
            text = text[:-3] + '.'
        # Если текст не заканчивается на точку, восклицательный или вопросительный знак
        elif not text[-1] in '.!?':
            words = text.split()
            if len(words) > 1:
                # Если последнее "слово" очень короткое (обрыв), удаляем его и ставим точку
                if len(words[-1]) <= 3:
                    text = ' '.join(words[:-1]) + '.'
                else:
                    text = text.rstrip('.,!?') + '.'
        return text
