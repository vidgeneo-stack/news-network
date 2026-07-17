from groq import Groq
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """ИИ делает краткий анонс с передачей главной сути"""
        
        prompt = f"""
Ты — профессиональный новостной редактор Telegram-канала.

ЗАДАЧА: Напиши КРАТКИЙ АНОНС новости, передающий ГЛАВНУЮ СУТЬ.

ПРАВИЛА:
1. Напиши 2-4 предложения, передающие самое важное
2. ПЕРЕФРАЗИРУЙ своими словами, не копируй оригинал
3. ТЕКСТ ДОЛЖЕН БЫТЬ ЗАВЕРШЁННЫМ — последнее предложение заканчивается точкой!
4. Не обрывай текст на полуслове!
5. Короткие предложения (10-15 слов)
6. Без клише: "по словам", "как сообщает", "отмечается"
7. Сохрани ключевые факты: имена, цифры, места
8. НЕЙТРАЛЬНЫЙ стиль

Заголовок: {title}
Оригинал: {content[:2000]}

Напиши ТОЛЬКО готовый анонс (без кавычек и пояснений):
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.75,
                max_tokens=2000,  # Большой лимит, пусть ИИ сам решит
                presence_penalty=0.5
            )
            
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Безопасная очистка
            rewritten = self._safe_fix_spacing(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            return self._safe_fix_spacing(content[:400]) if content else ""
    
    def _safe_fix_spacing(self, text: str) -> str:
        """БЕЗОПАСНО чинит только стыки слов"""
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        text = re.sub(r'([а-яё])([A-ZА-ЯЁ])', r'\1 \2', text)
        text = re.sub(r'([a-z])([А-Я])', r'\1 \2', text)
        text = re.sub(r'([А-Яа-яA-Za-z])\(', r'\1 (', text)
        text = re.sub(r'\)([А-Яа-яA-Za-z])', r') \1', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
