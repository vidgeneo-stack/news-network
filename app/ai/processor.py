import google.generativeai as genai
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        genai.configure(api_key=settings.GROQ_API_KEY)
        self.model = genai.GenerativeModel(settings.GROQ_MODEL)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        prompt = f"""
Ты — профессиональный новостной редактор Telegram-канала. Сделай качественный РЕРАЙТ новости.

ПРИМЕР РЕРАЙТА:
Оригинал: "Президент России Владимир Путин провел встречу с министрами правительства. На совещании обсуждались вопросы экономического развития страны. По словам пресс-секретаря, встреча длилась три часа."
Рерайт: "Глава государства встретился с членами кабинета министров. Главной темой переговоров стала экономика. Переговоры продолжались три часа."

ПРАВИЛА:
1. ПЕРЕФРАЗИРУЙ своими словами. Не копируй оригинальные фразы!
2. Напиши 2-4 предложения, передающие ГЛАВНУЮ СУТЬ новости.
3. ПРИНЦИП ПЕРЕВЕРНУТОЙ ПИРАМИДЫ: первое предложение — самое важное.
4. Короткие предложения (10-15 слов).
5. ЗАПРЕЩЕНЫ клише: "по словам", "как сообщает", "отмечается"
6. НЕЙТРАЛЬНЫЙ стиль.
7. Сохрани ВСЕ ключевые факты: имена, даты, цифры, места.
8. ТЕКСТ ДОЛЖЕН БЫТЬ ЗАВЕРШЁННЫМ — последнее предложение заканчивается точкой!
9. Не обрывай текст на полуслове!

Заголовок: {title}
Оригинал: {content[:2000]}

Напиши ТОЛЬКО готовый рерайт (без кавычек и пояснений):
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=800,
                )
            )
            
            rewritten = response.text.strip()
            rewritten = self._safe_fix_spacing(rewritten)
            rewritten = self._ensure_complete_sentence(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"Gemini ошибка: {e}")
            return self._safe_fix_spacing(content[:400]) if content else ""
    
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
