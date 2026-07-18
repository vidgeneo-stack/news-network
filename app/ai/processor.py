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
   Ты — профессиональный новостной редактор Telegram-канала. Сделай качественный РЕРАЙТ новости.

   ПРИМЕР РЕРАЙТА:
   Оригинал: "Президент России провел встречу с министрами. Обсуждались вопросы экономики."
   Рерайт: "Глава государства встретился с членами кабинета министров. Главной темой стала экономика."

   ПРАВИЛА:
   1. ПЕРЕФРАЗИРУЙ своими словами. Не копируй оригинальные фразы!
   2. Напиши 2-4 предложения, передающие ГЛАВНУЮ СУТЬ.
   3. Короткие предложения (10-15 слов).
   4. ЗАПРЕЩЕНЫ клише: "по словам", "как сообщает", "отмечается".
   5. Сохрани ВСЕ ключевые факты: имена, даты, цифры, места.
   6. ТЕКСТ ДОЛЖЕН БЫТЬ ЗАВЕРШЁННЫМ — последнее предложение обязательно заканчивается точкой!

   Заголовок: {title}
   Оригинал: {content[:2000]}

   Напиши ТОЛЬКО готовый рерайт (без кавычек и пояснений):
   """
           
           url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
           
           payload = {
               "contents": [{"parts": [{"text": prompt}]}],
               "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}
           }
           
           headers = {"Content-Type": "application/json"}
           
           try:
               # Делаем запрос через SOCKS5 прокси
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
           if not text[-1] in '.!?…':
               words = text.split()
               if len(words) > 1:
                   if len(words[-1]) <= 2:
                       text = ' '.join(words[:-1]) + '...'
                   else:
                       text = text.rstrip('.,!?') + '...'
           return text
