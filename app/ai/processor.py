from groq import Groq
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """Использует AI для создания красивого поста для Telegram"""
        
        prompt = f"""
Ты — профессиональный редактор новостного Telegram-канала.
У тебя есть заголовок новости и исходный текст.

Задача:
1. Напиши короткий, цепляющий анонс новости (лид) на основе текста. Максимум 3-4 предложения (около 300-400 символов).
2. Текст должен быть живым, грамотным и интересным.
3. НЕ используй markdown (жирный шрифт, курсив) в самом тексте анонса.
4. НЕ добавляй ссылки, хэштеги или призывы "читать далее". Просто чистый текст анонса.
5. Если исходный текст пустой или бессмысленный, напиши анонс только на основе заголовка.

Заголовок: {title}
Исходный текст: {content[:1000]}

Верни ТОЛЬКО текст анонса, без кавычек и лишних слов.
"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.7,
                max_tokens=300
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            # Если AI упал, возвращаем обрезанный исходный текст
            return content[:300].strip() if content else ""
