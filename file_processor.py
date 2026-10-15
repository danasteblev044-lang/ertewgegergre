import io
import base64
import zipfile
import xml.etree.ElementTree as ET
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Извлекает текст из PDF файла"""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages_text.append(f"--- Страница {i+1} ---\n{text.strip()}")
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.warning(f"Ошибка чтения PDF через pypdf: {e}")
        # Попытка простого извлечения строк
        try:
            import re
            strings = re.findall(rb'\((.*?)\)', file_bytes)
            decoded = [s.decode('latin1', errors='ignore') for s in strings if len(s) > 3]
            return "Извлеченный текст PDF:\n" + "\n".join(decoded[:200])
        except Exception:
            return f"Не удалось прочитать текст из PDF файла: {e}"

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Извлекает текст из DOCX документа (чистый Python через zipfile, без внешних библиотек)"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # Теги абзацев и текста в Word XML
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = []
            for p in tree.iterfind('.//w:p', namespaces):
                texts = [node.text for node in p.iterfind('.//w:t', namespaces) if node.text]
                if texts:
                    paragraphs.append(''.join(texts))
            return "\n".join(paragraphs)
    except Exception as e:
        return f"Не удалось прочитать текст из DOCX документа: {e}"

def extract_text_from_plain_text(file_bytes: bytes) -> str:
    """Пробует декодировать текстовые файлы (UTF-8, CP1251)"""
    for enc in ['utf-8', 'cp1251', 'latin1']:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode('utf-8', errors='replace')

def process_telegram_file(file_bytes: bytes, file_name: str, mime_type: str = "") -> Tuple[str, Optional[str]]:
    """
    Обрабатывает загруженный в Telegram файл.
    Возвращает:
      - (text_content, None) если это документ/текст
      - (text_caption, base64_image_url) если это изображение
    """
    fn_lower = file_name.lower()
    
    # 1. Если это изображение (фото, скриншот, документ-картинка)
    if (mime_type and mime_type.startswith("image/")) or fn_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
        b64 = base64.b64encode(file_bytes).decode('utf-8')
        fmt = "jpeg"
        if fn_lower.endswith('.png'): fmt = "png"
        elif fn_lower.endswith('.webp'): fmt = "webp"
        data_url = f"data:image/{fmt};base64,{b64}"
        return (f"[Изображение: {file_name}]", data_url)
        
    # 2. Если это PDF
    if fn_lower.endswith('.pdf') or mime_type == "application/pdf":
        text = extract_text_from_pdf(file_bytes)
        return (f"=== Содержимое документа PDF ({file_name}) ===\n{text}", None)
        
    # 3. Если это DOCX
    if fn_lower.endswith('.docx') or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_text_from_docx(file_bytes)
        return (f"=== Содержимое документа Word ({file_name}) ===\n{text}", None)
        
    # 4. Текстовые файлы, скрипты, разметка, код, конфиги
    text_extensions = ('.txt', '.py', '.js', '.ts', '.html', '.css', '.json', '.csv', '.md', '.log', '.xml', '.yaml', '.yml', '.ini', '.env')
    if fn_lower.endswith(text_extensions) or (mime_type and (mime_type.startswith("text/") or "json" in mime_type)):
        text = extract_text_from_plain_text(file_bytes)
        # Ограничиваем слишком гигантские файлы для контекста
        if len(text) > 40000:
            text = text[:40000] + "\n\n[Текст документа обрезан из-за большого размера]"
        return (f"=== Содержимое файла {file_name} ===\n{text}", None)
        
    # 5. Прочие файлы
    size_kb = len(file_bytes) / 1024
    return (f"[Прикреплен файл: {file_name}, размер: {size_kb:.1f} КБ, тип: {mime_type or 'неизвестен'}]", None)
