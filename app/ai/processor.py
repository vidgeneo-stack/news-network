from groq import Groq
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """AI делает настоящий рерайт с умной длиной"""
        
        # Определяем длину на основе исходного текста
        content_length = len(content)
        if content_length < 500:
            max_tokens = 400
            target_sentences = "2-3"
        elif content_length < 1500:
            max_tokens = 700
            target_sentences = "3-4"
        else:
            max_tokens = 1000  # Увеличили до 1000!
            target_sentences = "4-5"
        
        prompt = f"""
Ты — профессиональный журналист. Твоя задача — сделать НАСТОЯЩИЙ РЕРАЙТ новости для Telegram-канала.

ПРАВИЛА:
1. ПЕРЕФРАЗИРУЙ своими словами! Не копируй предложения из оригинала!
2. Напиши {target_sentences} предложения
3. ОБЯЗАТЕЛЬНО ставь пробелы после КАЖДОЙ точки, запятой, восклицательного знака
4. Не используй HTML-теги, markdown, звёздочки
5. Не добавляй ссылки, хэштеги, слова "источник" или "читать далее"
6. Передай главные факты новости
7. ЗАВЕРШИ текст полноценным предложением (не обрывай на полуслове!)

Заголовок: {title}
Оригинальный текст: {content[:1500]}

Напиши ТОЛЬКО готовый текст анонса (без кавычек и пояснений):
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.85,  # Больше креативности
                max_tokens=max_tokens
            )
            
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Агрессивная пост-обработка
            rewritten = self._fix_all_spacing(rewritten)
            rewritten = self._ensure_complete_sentence(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            return self._fix_all_spacing(content[:500]) if content else ""
    
    def _fix_all_spacing(self, text: str) -> str:
        """Агрессивно исправляет все проблемы с пробелами"""
        # Добавляем пробел после точек, если следующий символ - буква
        text = re.sub(r'([.!?])([А-Яа-яA-Za-zА-Я])', r'\1 \2', text)
        # Добавляем пробел после запятых, точек с запятой, двоеточий
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Исправляем слипшиеся слова (если между двумя словами нет пробела)
        text = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', text)  # Конец предложения + новое
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Для английских слов
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _ensure_complete_sentence(self, text: str) -> str:
        """Проверяет, что текст не обрывается на полуслове"""
        # Если текст заканчивается не на точку/восклицательный/вопросительный знак
        if text and not text[-1] in '.!?…':
            # Если последнее слово короткое (меньше 3 букв), возможно это обрыв
            last_word = text.split()[-1] if text.split() else ""
            if len(last_word) < 3:
                # Удаляем последнее слово и добавляем многоточие
                words = text.split()[:-1]
                text = ' '.join(words) + '...'
            else:
                # Добавляем многоточие
                text = text.rstrip('.,!?') + '...'
        return text
