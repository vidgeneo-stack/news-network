from groq import Groq
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """AI делает настоящий рерайт + определяет оптимальную длину"""
        
        # Определяем длину на основе исходного текста
        content_length = len(content)
        if content_length < 500:
            max_tokens = 200  # Короткие новости
            target_sentences = 2
        elif content_length < 1500:
            max_tokens = 400  # Средние новости
            target_sentences = 3
        else:
            max_tokens = 600  # Длинные новости
            target_sentences = 4
        
        prompt = f"""
Ты — профессиональный журналист и редактор новостного Telegram-канала.

ТВОЯ ЗАДАЧА:
1. СДЕЛАЙ НАСТОЯЩИЙ РЕРАЙТ (перефразируй своими словами, не копируй предложения дословно!)
2. Напиши цепляющий анонс новости на {target_sentences}-{target_sentences+1} предложения
3. Текст должен быть:
   - Живым, грамотным, легко читаемым
   - С ОБЯЗАТЕЛЬНЫМИ пробелами после точек, запятых и слов
   - Без HTML-тегов, markdown, звёздочек и подчёркиваний
   - Без ссылок, хэштегов и слов "источник", "читать далее"
4. Передай СУТЬ новости, сохранив главные факты
5. Если текст пустой — сделай рерайт только на основе заголовка

Заголовок: {title}
Исходный текст: {content[:1500]}

Верни ТОЛЬКО готовый текст анонса (без кавычек, без пояснений).
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.8,  # Больше креативности для рерайта
                max_tokens=max_tokens
            )
            
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Пост-обработка: гарантируем пробелы
            rewritten = self._fix_spacing(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            # Фолбэк: просто чистим текст
            return self._fix_spacing(content[:300]) if content else ""
    
    def _fix_spacing(self, text: str) -> str:
        """Исправляет отсутствующие пробелы"""
        # Добавляем пробелы после точек, запятых, если их нет
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
