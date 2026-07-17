from groq import Groq
from ..config import settings
import logging
import re

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def rewrite_for_telegram(self, title: str, content: str) -> str:
        """AI делает НАСТОЯЩИЙ рерайт с примером"""
        
        # Определяем длину
        content_length = len(content)
        if content_length < 500:
            max_tokens = 500
            target_sentences = "2-3"
        elif content_length < 1500:
            max_tokens = 800
            target_sentences = "3-4"
        else:
            max_tokens = 1000
            target_sentences = "4-5"
        
        prompt = f"""
Ты — профессиональный журналист. СДЕЛАЙ НАСТОЯЩИЙ РЕРАЙТ новости, отредактируй как профессионал. 

ПРИМЕР РЕРАЙТА:
Оригинал: "Президент России Владимир Путин провел встречу с министрами. На совещании обсуждались вопросы экономики."
Рерайт: "Глава государства встретился с членами правительства. Главной темой переговоров стали экономические вопросы."

ТВОЯ ЗАДАЧА:
1. ПЕРЕФРАЗИРУЙ каждое предложение своими словами!
2. Напиши {target_sentences} предложения
3. ОБЯЗАТЕЛЬНО ставь пробелы после точек, запятых, скобок
4. Не копируй фразы из оригинала!
5. ЗАВЕРШИ текст полноценным предложением!
6. Закончи мысль полностью логически! 
7. Проведи проверку на ошибки в грамматике и пунктуации! 

Заголовок: {title}
Оригинал: {content[:1500]}

Напиши ТОЛЬКО рерайт (без кавычек):
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.9,  # Максимум креативности
                max_tokens=max_tokens,
                presence_penalty=0.6,  # Штраф за копирование
                frequency_penalty=0.3
            )
            
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Проверяем, не скопировал ли AI текст
            if self._is_too_similar(rewritten, content):
                logger.warning("AI скопировал текст, перегенерируем...")
                return self._force_rewrite(title, content, max_tokens)
            
            # Агрессивная очистка
            rewritten = self._fix_all_spacing(rewritten)
            rewritten = self._ensure_complete_sentence(rewritten)
            
            return rewritten
            
        except Exception as e:
            logger.error(f"AI ошибка: {e}")
            return self._fix_all_spacing(content[:500]) if content else ""
    
    def _force_rewrite(self, title: str, content: str, max_tokens: int) -> str:
        """Принудительный рерайт с ещё более жёстким промптом"""
        prompt = f"""
ПЕРЕФРАЗИРУЙ этот текст ПОЛНОСТЬЮ своими словами. Не используй оригинальные фразы!

Заголовок: {title}
Текст: {content[:1000]}

Напиши 3 предложения своими словами:
"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=1.0,
                max_tokens=max_tokens,
                presence_penalty=0.8
            )
            return self._fix_all_spacing(chat_completion.choices[0].message.content.strip())
        except:
            return self._fix_all_spacing(content[:500])
    
    def _is_too_similar(self, rewritten: str, original: str) -> bool:
        """Проверяет, не скопировал ли AI текст"""
        if not rewritten or not original:
            return False
        
        # Берём первые 100 символов
        short_rewritten = rewritten[:100].lower()
        short_original = original[:100].lower()
        
        # Если совпадает больше 70% - это копипаст
        common_chars = sum(1 for a, b in zip(short_rewritten, short_original) if a == b)
        similarity = common_chars / max(len(short_rewritten), len(short_original))
        
        return similarity > 0.7
    
    def _fix_all_spacing(self, text: str) -> str:
        """Мощная очистка пробелов"""
        # Пробел после точек, восклицательных, вопросительных знаков
        text = re.sub(r'([.!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Пробел после запятых, двоеточий, точек с запятой
        text = re.sub(r'([,;:])([А-Яа-яA-Za-z])', r'\1 \2', text)
        # Пробел перед открывающей скобкой
        text = re.sub(r'([А-Яа-яA-Za-z])\(', r'\1 (', text)
        # Пробел после закрывающей скобки
        text = re.sub(r'\)([А-Яа-яA-Za-z])', r') \1', text)
        # Пробел между латиницей и кириллицей
        text = re.sub(r'([a-zA-Z])([А-Яа-я])', r'\1 \2', text)
        text = re.sub(r'([А-Яа-я])([a-zA-Z])', r'\1 \2', text)
        # Исправляем прилипшие предлоги (о, об, в, на, с, по, из, за, под, над, от, до, к)
        text = re.sub(r'([а-яё])(о|об|в|на|с|по|из|за|под|над|от|до|к)([А-Яа-я])', r'\1 \2 \3', text, flags=re.IGNORECASE)
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _ensure_complete_sentence(self, text: str) -> str:
        """Проверяет завершённость текста"""
        if text and not text[-1] in '.!?…':
            last_word = text.split()[-1] if text.split() else ""
            if len(last_word) < 4:
                words = text.split()[:-1]
                text = ' '.join(words) + '...'
            else:
                text = text.rstrip('.,!?') + '...'
        return text
