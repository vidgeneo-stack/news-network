from groq import Groq
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """ИИ делает профессиональный рерайт с самопроверкой"""
        
        content_length = len(content)
        if content_length < 500:
            max_tokens = 500
            sentences = "2-3"
        elif content_length < 1500:
            max_tokens = 700
            sentences = "3-4"
        else:
            max_tokens = 900
            sentences = "4-5"
        
        prompt = f"""
Ты — профессиональный новостной редактор Telegram-канала. Сделай РЕРАЙТ новости.

ПРИМЕР РЕРАЙТА:
Оригинал: "Президент России Владимир Путин провел встречу с министрами правительства. На совещании обсуждались вопросы экономического развития страны. По словам пресс-секретаря, встреча длилась три часа."
Рерайт: "Глава государства встретился с членами кабинета министров. Главной темой переговоров стала экономика. Переговоры продолжались три часа."

ПРАВИЛА:
1. ПЕРЕФРАЗИРУЙ своими словами. Не копируй оригинальные фразы!
2. Напиши {sentences} предложения.
3. ПРИНЦИП ПЕРЕВЕРНУТОЙ ПИРАМИДЫ: первое предложение — самое важное.
4. Короткие предложения (10-15 слов). Telegram не любит длинные!
5. ЗАПРЕЩЕНЫ клише: "по словам", "как сообщает", "отмечается", "сообщает источник"
6. НЕЙТРАЛЬНЫЙ стиль, без эмоций и оценок.
7. Сохрани ВСЕ ключевые факты: имена, даты, цифры, места.

САМОПРОВЕРКА перед отправкой:
- Все ли предложения закончены? (нет обрывов)
- Есть ли пробелы после точек и запятых?
- Нет ли скопированных фраз из оригинала?
- Понятен ли текст без чтения оригинала?

Заголовок: {title}
Оригинал: {content[:1500]}

Напиши ТОЛЬКО готовый рерайт (без кавычек, пояснений и слова "источник"):
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.75,
                max_tokens=max_tokens,
                presence_penalty=0.5,  # Штраф за копирование
                frequency_penalty=0.3  # Разнообразие слов
            )
            
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Самопроверка: если текст слишком похож на оригинал, перегенерируем
            if self._is_too_similar(rewritten, content):
                logger.warning("Текст слишком похож на оригинал, перегенерируем...")
                return self._force_rewrite(title, content, max_tokens)
            
            # Безопасная очистка
            rewritten = self._safe_fix_spacing(rewritten)
            rewritten = self._ensure_complete_sentence(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            return self._safe_fix_spacing(content[:400]) if content else ""
    
    def _force_rewrite(self, title: str, content: str, max_tokens: int) -> str:
        """Принудительный рерайт с ещё более жёсткими требованиями"""
        prompt = f"""
СДЕЛАЙ РЕРАЙТ этого текста. НЕ КОПИРУЙ оригинальные предложения!

ПРИМЕР:
Оригинал: "Министр иностранных дел России Сергей Лавров заявил о готовности к переговорам."
Рерайт: "Глава российской дипломатии выразил готовность вести диалог."

Заголовок: {title}
Текст: {content[:1000]}

Напиши {3 if len(content) < 1000 else 4} коротких предложения своими словами:
"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.85,
                max_tokens=max_tokens,
                presence_penalty=0.7
            )
            return self._safe_fix_spacing(chat_completion.choices[0].message.content.strip())
        except:
            return self._safe_fix_spacing(content[:400])
    
    def _is_too_similar(self, rewritten: str, original: str) -> bool:
        """Проверяет, не скопировал ли ИИ текст"""
        if not rewritten or not original:
            return False
        
        # Берём первые 150 символов
        short_rewritten = rewritten[:150].lower()
        short_original = original[:150].lower()
        
        # Считаем совпадения
        common_chars = sum(1 for a, b in zip(short_rewritten, short_original) if a == b)
        similarity = common_chars / max(len(short_rewritten), len(short_original))
        
        # Если совпадает больше 60% — это копипаст
        return similarity > 0.6
    
    def _safe_fix_spacing(self, text: str) -> str:
        """БЕЗОПАСНО чинит только стыки слов"""
        # Пробел после точек, восклицательных и вопросительных знаков
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Пробел после запятых, двоеточий и точек с запятой
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Пробел между строчной кириллицей и заглавной буквой
        text = re.sub(r'([а-яё])([A-ZА-ЯЁ])', r'\1 \2', text)
        # Пробел между строчной латиницей и заглавной кириллицей
        text = re.sub(r'([a-z])([А-Я])', r'\1 \2', text)
        # Пробелы вокруг скобок
        text = re.sub(r'([А-Яа-яA-Za-z])\(', r'\1 (', text)
        text = re.sub(r'\)([А-Яа-яA-Za-z])', r') \1', text)
        # Удаляем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _ensure_complete_sentence(self, text: str) -> str:
        """Гарантирует завершённость текста"""
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
