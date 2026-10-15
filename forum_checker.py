import aiohttp
import asyncio
import re
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import config
import database

logger = logging.getLogger(__name__)

# Заголовки реального браузера для обхода базовых проверок
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

# Ключевые слова префиксов / статусов рассмотренных тем (которые нужно игнорировать)
REVIEWED_STATUS_KEYWORDS = [
    "рассмотрено",
    "закрыто",
    "отклонено",
    "одобрено",
    "решено",
    "отказано",
    "архив",
    "выполнено",
    "неактуально"
]

async def fetch_forum_html(url: str) -> Optional[str]:
    """Асинхронно получает HTML страницы форума"""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Форум вернул статус {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Ошибка при запросе к форуму Majestic RP: {e}")
        return None

def parse_complaints(html: str, target_nick: str = "Eskalane") -> List[Dict[str, str]]:
    """
    Парсит темы форума XenForo и находит активные (нерассмотренные) жалобы на указанный ник.
    """
    soup = BeautifulSoup(html, "html.parser")
    found_complaints = []
    
    # В XenForo темы обычно обернуты в .structItem--thread
    thread_items = soup.select("div.structItem--thread")
    if not thread_items:
        # Резервный селектор
        thread_items = soup.select(".structItem")
        
    nick_clean = target_nick.lower().strip()
    
    for item in thread_items:
        # Проверяем префиксы темы (статус рассмотрения)
        prefix_elems = item.select(".labelLink, .label, span[class*='label--']")
        prefixes = [p.get_text(strip=True).lower() for p in prefix_elems]
        prefix_text = " ".join(prefixes)
        
        # Если в префиксах есть маркер, что жалоба рассмотрена/закрыта — пропускаем
        is_reviewed = any(keyword in prefix_text for keyword in REVIEWED_STATUS_KEYWORDS)
        if is_reviewed:
            continue
            
        # Также проверяем иконку замка (закрытая тема)
        if item.select(".structItem-status--locked, [title*='Закрыто']"):
            continue

        # Заголовок темы
        title_elem = item.select_one(".structItem-title a")
        if not title_elem:
            continue
            
        title = title_elem.get_text(strip=True)
        href = title_elem.get("href", "")
        
        # Полная ссылка на тему
        if href.startswith("/"):
            full_url = "https://forum.majestic-rp.ru" + href
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = "https://forum.majestic-rp.ru/forums/" + href
            
        # Извлекаем ID темы из URL (например: /threads/zhaloba-na-eskalane.12345/ -> 12345)
        id_match = re.search(r'\.(\d+)/?$', href)
        thread_id = id_match.group(1) if id_match else href
        
        # Автор темы
        author_elem = item.select_one(".username, .structItem-parts .username")
        author = author_elem.get_text(strip=True) if author_elem else "Неизвестный"
        
        # Дата/время создания
        time_elem = item.select_one("time.u-dt")
        created_time = time_elem.get("title", "") if time_elem else ""
        if not created_time and time_elem:
            created_time = time_elem.get_text(strip=True)
            
        # Проверяем, упоминается ли ник Eskalane / Eskalane Helper в заголовке
        # (или в тексте превью, если есть)
        title_lower = title.lower()
        if "eskalane" in title_lower or nick_clean in title_lower:
            found_complaints.append({
                "thread_id": thread_id,
                "title": title,
                "url": full_url,
                "author": author,
                "created_time": created_time,
                "prefix": prefix_text
            })
            
    return found_complaints

async def check_new_complaints(auto_mark_seen: bool = True) -> List[Dict[str, str]]:
    """
    Проверяет жалобы на форуме. Возвращает только те, о которых пользователь еще не был уведомлен!
    """
    html = await fetch_forum_html(config.MAJESTIC_FORUM_URL)
    if not html:
        return []
        
    complaints = parse_complaints(html, config.MAJESTIC_NICKNAME)
    new_unseen_complaints = []
    
    for comp in complaints:
        thread_id = comp["thread_id"]
        if not database.is_complaint_seen(thread_id):
            new_unseen_complaints.append(comp)
            if auto_mark_seen:
                database.mark_complaint_seen(thread_id, comp["title"], comp["url"])
                
    return new_unseen_complaints

def format_complaints_alert(complaints: List[Dict[str, str]]) -> str:
    """Форматирует найденные жалобы в тревожное уведомление для Telegram"""
    if not complaints:
        return ""
        
    text = (
        "🚨 <b>ВНИМАНИЕ! ОБНАРУЖЕНА ЖАЛОБА НА ВАС!</b> 🚨\n"
        f"Сервер: <b>Majestic RP Memphis</b>\n"
        f"Администратор: <b>{config.MAJESTIC_NICKNAME}</b>\n"
        f"{'—'*26}\n"
    )
    
    for i, c in enumerate(complaints, 1):
        text += (
            f"⚠️ <b>Жалоба #{i}:</b> <a href=\"{c['url']}\">{c['title']}</a>\n"
            f"👤 Автор: <b>{c['author']}</b>\n"
            f"🕒 Время: <i>{c.get('created_time', 'Недавно')}</i>\n"
            f"🔗 <a href=\"{c['url']}\">Перейти к жалобе на форуме</a>\n\n"
        )
    return text
