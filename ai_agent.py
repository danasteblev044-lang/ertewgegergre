import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from openai import AsyncOpenAI

import config
import database
import schedule_data
import forum_checker
import web_search

logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI (совместимого с PlusVibe API)
client = AsyncOpenAI(
    api_key=config.PLUSVIBE_API_KEY or "no-key-set",
    base_url=config.PLUSVIBE_BASE_URL
)

# Определение инструментов (Tools / Function Calling)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_schedule",
            "description": "Получить расписание занятий группы П1-25В на любой день (сегодня, завтра, послезавтра, конкретный день недели, дата) с учетом числителя и знаменателя.",
            "parameters": {
                "type": "object",
                "properties": {
                    "day_query": {
                        "type": "string",
                        "description": "Запрос дня: 'сегодня', 'завтра', 'послезавтра', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота' или дата."
                    }
                },
                "required": ["day_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_forum_complaints",
            "description": "Проверить наличие новых активных (нерассмотренных) жалоб на администратора Eskalane Helper на форуме Majestic RP Memphis.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_internet",
            "description": "Выполнить поиск актуальной информации в интернете через поисковую систему.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_user_fact",
            "description": "Сохранить новый факт, предпочтение, информацию о пользователе в долговременную память.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Краткий идентификатор факта (на латинице, например favorite_game, hobby, friend_name)"
                    },
                    "value": {
                        "type": "string",
                        "description": "Описание факта на русском языке"
                    }
                },
                "required": ["key", "value"]
            }
        }
    }
]

def build_system_prompt() -> str:
    """Формирует системный промпт агента с памятью, фактами и расписанием"""
    now = datetime.now()
    today_str = now.strftime("%d.%m.%Y (%A)")
    curr_week_type = schedule_data.get_week_type(now.date())
    
    memory_facts = database.format_user_profile_prompt()
    
    return f"""Тебя зовут Селеста (Selesta). Ты — персональный умный ИИ-ассистент, верная подруга и цифровой спутник пользователя в Telegram.
Ты говоришь о себе в женском роде (посмотрела, проверила, нашла, готова помочь).
Ты обладаешь собственной памятью, умеешь выходить в интернет, анализировать любые присланные файлы, документы и фотографии.

Сегодняшняя дата: {today_str}
Текущая учебная неделя: {curr_week_type.upper()}

=== ЧТО ТЫ ЗНАЕШЬ О ПОЛЬЗОВАТЕЛЕ (ДОЛГОВРЕМЕННАЯ ПАМЯТЬ) ===
- Твой пользователь — администратор на сервере Majestic RP Memphis под ником "{config.MAJESTIC_NICKNAME}".
- Он учится в колледже ОГБПОУ СОТА в группе П1-25В (специальность: 09.02.07 Информационные системы и программирование, 2 курс).
- В расписании группы П1-25В недели чередуются на ЧИСЛИТЕЛЬ и ЗНАМЕНАТЕЛЬ. Неделя с 12.10.2026 — числитель.
- Ты всегда знаешь точное расписание пар на сегодня, завтра, послезавтра и любой другой день через инструмент get_schedule.
- Ты внимательно следишь за жалобами на администрацию на форуме Majestic RP (раздел: https://forum.majestic-rp.ru/forums/zhaloby-na-administratsiyu.1519/).
{memory_facts}

=== ТВОИ ПРАВИЛА И ХАРАКТЕР ===
1. Твое имя — Селеста. Общайся уважительно, тепло, дружелюбно, с заботой и по делу. Обращайся к пользователю на "ты".
2. Если пользователь спрашивает про расписание (сегодня, завтра, понедельник и т.д.) или какая сейчас неделя (числитель/знаменатель) — используй функцию get_schedule или отвечай прямо и точно, указывая номер пары, время, предмет, преподавателя и номер кабинета.
3. Если пользователь просит найти что-то в интернете или вопрос требует актуальных свежих данных — вызывай search_internet.
4. Если пользователь делится важной информацией о себе (планы, привычки, предпочтения) — используй remember_user_fact, чтобы запомнить это навсегда.
5. При получении фото или документов внимательно изучай их и отвечай на вопросы по их содержимому.
6. Отвечай на русском языке с аккуратным и красивым форматированием (абзацы, эмодзи, списки).
"""

async def execute_tool(name: str, args: dict) -> str:
    """Выполняет вызов инструмента (tool) и возвращает строковый результат"""
    try:
        if name == "get_schedule":
            query = args.get("day_query", "сегодня")
            return schedule_data.get_schedule_by_relative_query(query)
            
        elif name == "check_forum_complaints":
            new_complaints = await forum_checker.check_new_complaints(auto_mark_seen=True)
            if not new_complaints:
                return "Новых нерассмотренных жалоб на форуме Majestic RP на ваш ник не обнаружено. Всё спокойно!"
            return forum_checker.format_complaints_alert(new_complaints)
            
        elif name == "search_internet":
            query = args.get("query", "")
            results = await web_search.search_duckduckgo(query)
            return web_search.format_search_results(results)
            
        elif name == "remember_user_fact":
            key = args.get("key", "")
            value = args.get("value", "")
            if key and value:
                database.set_user_fact(key, value)
                return f"Успешно запомнил в профиль: {value}"
            return "Не удалось сохранить факт: пустой ключ или значение."
            
        else:
            return f"Неизвестный инструмент: {name}"
    except Exception as e:
        logger.error(f"Ошибка выполнения инструмента {name}: {e}")
        return f"Ошибка при выполнении действия {name}: {str(e)}"

async def ask_agent(
    chat_id: int,
    user_text: str,
    image_url: Optional[str] = None
) -> str:
    """
    Основная точка входа для общения с ИИ-агентом.
    Сохраняет историю сообщений, запускает модель, выполняет тулы и возвращает ответ.
    """
    # 1. Получаем историю предыдущих сообщений из SQLite
    history = database.get_recent_messages(chat_id, limit=12)
    
    # 2. Формируем список сообщений для OpenAI API
    messages = [{"role": "system", "content": build_system_prompt()}]
    
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
        
    # 3. Добавляем новое сообщение пользователя
    if image_url:
        user_content: Any = [
            {"type": "text", "text": user_text or "Посмотри на это изображение и прокомментируй/ответь на вопрос."},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    else:
        user_content = user_text
        
    messages.append({"role": "user", "content": user_content})
    
    # 4. Цикл вызова LLM и выполнения функций (Tools)
    max_turns = 5
    turn = 0
    
    while turn < max_turns:
        turn += 1
        try:
            response = await client.chat.completions.create(
                model=config.AI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            logger.error(f"Ошибка запроса к PlusVibe API: {e}")
            err_msg = str(e)
            if "api_key" in err_msg.lower() or "unauthorized" in err_msg.lower() or "401" in err_msg:
                return "⚠️ <b>Ошибка авторизации API:</b> Проверьте, что в файле <code>.env</code> указан правильный ключ <code>PLUSVIBE_API_KEY</code>."
            return f"⚠️ Произошла ошибка при обращении к языковой модели: <code>{err_msg}</code>"
            
        resp_msg = response.choices[0].message
        messages.append(resp_msg)
        
        # Если модель не запрашивает инструменты, завершаем цикл
        if not resp_msg.tool_calls:
            assistant_reply = resp_msg.content or ""
            # Сохраняем в историю диалога
            database.add_message(chat_id, "user", user_text if not image_url else f"{user_text} [вложено изображение]")
            database.add_message(chat_id, "assistant", assistant_reply)
            return assistant_reply
            
        # Выполняем каждый вызванный инструмент
        for tool_call in resp_msg.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except Exception:
                func_args = {}
                
            tool_result = await execute_tool(func_name, func_args)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            })
            
    # Если за 5 итераций не получили финальный текст
    final_text = messages[-1].get("content", "Действие выполнено.")
    database.add_message(chat_id, "user", user_text)
    database.add_message(chat_id, "assistant", str(final_text))
    return str(final_text)
