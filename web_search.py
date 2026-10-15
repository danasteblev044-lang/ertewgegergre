import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

async def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Выполняет поиск в интернете через DuckDuckGo HTML без необходимости в API-ключах.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    results = []
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.post("https://html.duckduckgo.com/html/", data={"q": query}) as response:
                if response.status != 200:
                    logger.warning(f"DuckDuckGo status {response.status}")
                    return results
                html = await response.text()
                
        soup = BeautifulSoup(html, "html.parser")
        result_divs = soup.select(".result")
        
        for div in result_divs:
            title_elem = div.select_one(".result__title a")
            snippet_elem = div.select_one(".result__snippet")
            
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            raw_url = title_elem.get("href", "")
            
            # Извлекаем реальный URL из редиректа DDG
            clean_url = raw_url
            if "uddg=" in raw_url:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                clean_url = parsed.get("uddg", [raw_url])[0]
                
            results.append({
                "title": title,
                "snippet": snippet,
                "url": clean_url
            })
            
            if len(results) >= max_results:
                break
                
    except Exception as e:
        logger.error(f"Ошибка при веб-поиске DuckDuckGo: {e}")
        
    return results

def format_search_results(results: List[Dict[str, str]]) -> str:
    if not results:
        return "По вашему запросу в интернете ничего не найдено."
        
    formatted = ["Результаты поиска в интернете:"]
    for i, r in enumerate(results, 1):
        formatted.append(f"{i}. {r['title']}\n   {r['snippet']}\n   Ссылка: {r['url']}")
    return "\n\n".join(formatted)
