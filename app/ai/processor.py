from openai import OpenAI
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.AI_API_KEY
        )
        self.model = settings.AI_MODEL

    def rewrite_for_telegram(self, title: str, content: str) -> str | None:
        prompt = f"""<task>
Ты — профессиональный новостной редактор Telegram-канала. Сделай качественный, компактный рерайт новости своими словами.
</task>

<rules>
1. Напиши связный, грамотный текст, передающий главную суть.
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
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=800,
                extra_body={"reasoning": {"enabled": True}}  # Твой параметр из скрипта
            )
            
            rewritten = response.choices[0].message.content.strip()
            rewritten = self._safe_fix_spacing(rewritten)
            rewritten = self._ensure_complete_sentence(rewritten)
            return rewritten
            
        except Exception as e:
            logger.error(f"OpenRouter ошибка: {e}")
            return None
    
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
