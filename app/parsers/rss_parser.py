import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional

class RSSParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def parse_feed(self, url: str, limit: int = 100) -> List[Dict]:
        """Парсит RSS ленту и возвращает список новостей"""
        try:
            response = httpx.get(url, headers=self.headers, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            
            news_list = []
            for entry in feed.entries[:limit]:
                # Получаем краткое описание из RSS
                content = entry.get('summary', entry.get('description', ''))
                
                # Если текста очень мало, пробуем скачать полную статью
                link = entry.get('link') or entry.get('id') or ''
                if len(content) < 150 and link:
                    full_text = self._scrape_full_text(link)
                    if full_text:
                        content = full_text

                # Ищем картинку
                image_url = self._extract_image(entry)

                news_list.append({
                    'title': entry.get('title', 'Без заголовка')[:500],
                    'content': content,
                    'source_url': link,
                    'image_url': image_url,
                    'published_at': self._parse_date(entry)
                })
            return news_list
        except Exception as e:
            print(f"Ошибка парсинга {url}: {e}")
            return []

    def _scrape_full_text(self, url: str) -> Optional[str]:
        """Скачивает полный текст со страницы"""
        try:
            response = httpx.get(url, headers=self.headers, follow_redirects=True, timeout=10.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = soup.find_all('p')
                text_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
                full_text = '\n\n'.join(text_parts)
                return full_text if len(full_text) > 200 else None
        except Exception:
            pass
        return None

    def _extract_image(self, entry) -> Optional[str]:
        """Пытается найти картинку в RSS"""
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0]['url']
        if 'enclosures' in entry:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href')
        return None

    def _parse_date(self, entry) -> datetime:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass
        return datetime.now()
