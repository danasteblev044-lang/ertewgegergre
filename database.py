import sqlite3
import json
import time
from typing import List, Dict, Optional, Any
import config

def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица истории сообщений (краткосрочная память диалога)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    )
    """)
    
    # Таблица долговременных фактов о пользователе (профиль)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        updated_at REAL NOT NULL
    )
    """)
    
    # Таблица уже просмотренных/уведомленных жалоб на форуме Majestic RP
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seen_complaints (
        thread_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        first_seen_at REAL NOT NULL
    )
    """)
    
    # Таблица состояния бота (время последней активности пользователя, время последней проверки)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_state (
        state_key TEXT PRIMARY KEY,
        state_value TEXT NOT NULL,
        updated_at REAL NOT NULL
    )
    """)
    
    conn.commit()
    
    # Заполняем базовые факты о пользователе, если еще не заполнены
    default_facts = {
        "user_role": "Администратор на Majestic RP Memphis (никнейм Eskalane Helper)",
        "college": "Студент ОГБПОУ СОТА (Смоленская областная технологическая академия)",
        "group": "Группа П1-25В, специальность 09.02.07 Информационные системы и программирование, 2 курс",
        "schedule_info": "Расписание на 1 семестр 2026-2027 загружено в память бота, поддерживает деление на числитель и знаменатель (неделя с 12.10.2026 — числитель)",
        "forum_monitoring": "Мониторинг раздела 'Жалобы на администрацию' на форуме Majestic RP по нику Eskalane Helper"
    }
    
    for k, v in default_facts.items():
        cursor.execute("""
        INSERT OR IGNORE INTO user_memory (key, value, updated_at)
        VALUES (?, ?, ?)
        """, (k, v, time.time()))
        
    conn.commit()
    conn.close()

# --- Управление историей сообщений ---

def add_message(chat_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO chat_history (chat_id, role, content, created_at)
    VALUES (?, ?, ?, ?)
    """, (chat_id, role, content, time.time()))
    conn.commit()
    conn.close()

def get_recent_messages(chat_id: int, limit: int = 16) -> List[Dict[str, str]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT role, content FROM (
        SELECT id, role, content FROM chat_history
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
    ) ORDER BY id ASC
    """, (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def clear_chat_history(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# --- Долговременная память пользователя ---

def set_user_fact(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_memory (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, value, time.time()))
    conn.commit()
    conn.close()

def get_all_user_facts() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_memory")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def format_user_profile_prompt() -> str:
    facts = get_all_user_facts()
    if not facts:
        return ""
    lines = ["Факты и профиль пользователя (сохранены в памяти):"]
    for k, v in facts.items():
        lines.append(f"- {v}")
    return "\n".join(lines)

# --- Управление просмотренными жалобами ---

def is_complaint_seen(thread_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_complaints WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def mark_complaint_seen(thread_id: str, title: str, url: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO seen_complaints (thread_id, title, url, first_seen_at)
    VALUES (?, ?, ?, ?)
    """, (thread_id, title, url, time.time()))
    conn.commit()
    conn.close()

# --- Управление состоянием бота (время взаимодействия) ---

def set_state(key: str, value: Any):
    conn = get_connection()
    cursor = conn.cursor()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute("""
    INSERT INTO bot_state (state_key, state_value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value, updated_at = excluded.updated_at
    """, (key, val_str, time.time()))
    conn.commit()
    conn.close()

def get_state(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT state_value FROM bot_state WHERE state_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return default
    try:
        return json.loads(row["state_value"])
    except Exception:
        return row["state_value"]

# Инициализируем БД при импорте
init_db()
