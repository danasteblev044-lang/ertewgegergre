from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import config

# Дни недели на русском
DAYS_OF_WEEK = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]

# Стандартное время пар для удобства студента
PAIR_TIMES = {
    1: "08:30 – 10:00",
    2: "10:10 – 11:40",
    3: "12:10 – 13:40",
    4: "13:50 – 15:20",
    5: "15:30 – 17:00",
}

# Расписание для группы П 1-25В (1 семестр 2026-2027)
# Если предмет одинаковый обе недели - ключ "все".
# Если предмет разделяется - ключи "числитель" и "знаменатель".
SCHEDULE_P125V: Dict[str, Dict[int, Dict[str, dict]]] = {
    "Понедельник": {
        1: {
            "все": {
                "code": "ОП.14",
                "name": "Администрирование компьютерных сетей",
                "teacher": "Алешин А.А.",
                "room": "Б316"
            }
        },
        2: {
            "все": {
                "code": "ОГСЭ.02",
                "name": "История",
                "teacher": "Воробьева К.А.",
                "room": "211"
            }
        },
        3: {
            "все": {
                "code": "ООД.04",
                "name": "Обществознание",
                "teacher": "Туева Л.С.",
                "room": "303"
            }
        },
        4: {
            "все": {
                "code": "ООД.05",
                "name": "География",
                "teacher": "Кишкунова А.А.",
                "room": "108"
            }
        },
        5: {
            "все": {
                "code": "ОП.14",
                "name": "Администрирование компьютерных сетей",
                "teacher": "Алешин А.А.",
                "room": "Б316"
            }
        }
    },
    "Вторник": {
        1: {
            "все": {
                "code": "ОП.12",
                "name": "Менеджмент в профессиональной деятельности",
                "teacher": "Парамонова М.Н.",
                "room": "Б316"
            }
        },
        2: {
            "все": {
                "code": "ООД.05",
                "name": "География",
                "teacher": "Кишкунова А.А.",
                "room": "108"
            }
        }
    },
    "Среда": {
        1: {
            "все": {
                "code": "ЕН.02",
                "name": "Дискретная математика с элементами математической логики",
                "teacher": "Головлев А.И.",
                "room": "403"
            }
        },
        2: {
            "все": {
                "code": "ОГСЭ.05",
                "name": "Физическая культура",
                "teacher": "Воробьева О.В.",
                "room": "с/з"
            }
        },
        3: {
            "все": {
                "code": "ООД.02",
                "name": "Литература",
                "teacher": "Агаркова Е.Б.",
                "room": "123"
            }
        },
        4: {
            "все": {
                "code": "ООД.02",
                "name": "Литература",
                "teacher": "Агаркова Е.Б.",
                "room": "123"
            }
        }
    },
    "Четверг": {
        1: {
            "все": {
                "code": "ОП.08",
                "name": "Основы проектирования баз данных",
                "teacher": "Якуненкова И.А.",
                "room": "306"
            }
        },
        2: {
            "все": {
                "code": "ОП.03",
                "name": "Информационные технологии",
                "teacher": "Крупенева А.М.",
                "room": "404"
            }
        },
        3: {
            "числитель": {
                "code": "ОГСЭ.02",
                "name": "История",
                "teacher": "Воробьева К.А.",
                "room": "211"
            },
            "знаменатель": {
                "code": "ОП.03",
                "name": "Информационные технологии",
                "teacher": "Крупенева А.М.",
                "room": "404"
            }
        }
    },
    "Пятница": {
        1: {
            "все": {
                "code": "ОП.04",
                "name": "Основы алгоритмизации и программирования",
                "teacher": "Якуненкова И.А.",
                "room": "306"
            }
        },
        2: {
            "все": {
                "code": "ОГСЭ.04",
                "name": "Иностранный язык в профессиональной деятельности",
                "teacher": "Масленкина С.А.",
                "room": "308"
            }
        },
        3: {
            "все": {
                "code": "МДК.01.01",
                "name": "Разработка программных модулей",
                "teacher": "Головлев А.И.",
                "room": "403"
            }
        }
    },
    "Суббота": {
        2: {
            "все": {
                "code": "ЕН.01",
                "name": "Элементы высшей математики",
                "teacher": "Алексеенкова В.А.",
                "room": "303"
            }
        },
        3: {
            "все": {
                "code": "МДК.04.01",
                "name": "Внедрение и поддержка программного обеспечения компьютерных систем",
                "teacher": "Алешин А.А.",
                "room": "Б316"
            }
        }
    },
    "Воскресенье": {}
}


def get_week_type(target_date: Optional[date] = None) -> str:
    """
    Определяет тип недели ('числитель' или 'знаменатель') относительно опорной недели.
    Опорная неделя: config.ANCHOR_MONDAY, тип: config.ANCHOR_WEEK_TYPE ('числитель').
    """
    if target_date is None:
        target_date = date.today()
        
    # Находим понедельник целевой недели
    target_monday = target_date - timedelta(days=target_date.weekday())
    anchor_monday = config.ANCHOR_MONDAY
    
    diff_days = (target_monday - anchor_monday).days
    diff_weeks = diff_days // 7
    
    if diff_weeks % 2 == 0:
        return config.ANCHOR_WEEK_TYPE
    else:
        return "знаменатель" if config.ANCHOR_WEEK_TYPE == "числитель" else "числитель"


def get_schedule_for_date(target_date: date) -> Tuple[str, str, List[dict]]:
    """
    Возвращает (день_недели, тип_недели, список_пар) для указанной даты.
    """
    day_name = DAYS_OF_WEEK[target_date.weekday()]
    week_type = get_week_type(target_date)
    day_schedule = SCHEDULE_P125V.get(day_name, {})
    
    lessons = []
    for pair_num in sorted(day_schedule.keys()):
        pair_data = day_schedule[pair_num]
        lesson_info = None
        
        if "все" in pair_data:
            lesson_info = dict(pair_data["все"])
        elif week_type in pair_data:
            lesson_info = dict(pair_data[week_type])
            
        if lesson_info:
            lesson_info["pair_num"] = pair_num
            lesson_info["time"] = PAIR_TIMES.get(pair_num, "")
            lessons.append(lesson_info)
            
    return day_name, week_type, lessons


def format_schedule(target_date: date) -> str:
    """
    Форматирует расписание на дату в красивый читаемый текст для пользователя.
    """
    day_name, week_type, lessons = get_schedule_for_date(target_date)
    date_str = target_date.strftime("%d.%m.%Y")
    
    header = (
        f"📅 <b>Расписание группы П1-25В</b>\n"
        f"🗓 <b>{day_name}, {date_str}</b>\n"
        f"🔄 Неделя: <b>{week_type.upper()}</b>\n"
        f"{'—'*24}\n"
    )
    
    if not lessons:
        if day_name == "Воскресенье":
            return header + "🎉 <b>Воскресенье — законный выходной! Пар нет, отдыхай!</b>"
        return header + "✨ <b>В этот день пар нет! Можно выдохнуть.</b>"
        
    lines = []
    for l in lessons:
        lines.append(
            f"<b>{l['pair_num']}-я пара</b> ({l['time']}):\n"
            f"  📚 <b>{l['code']} {l['name']}</b>\n"
            f"  👨‍🏫 {l['teacher']} | 🚪 каб. <b>{l['room']}</b>\n"
        )
        
    return header + "\n".join(lines)


def get_schedule_by_relative_query(query: str, current_date: Optional[date] = None) -> str:
    """
    Парсит естественные запросы ('сегодня', 'завтра', 'послезавтра', день недели) и возвращает расписание.
    """
    if current_date is None:
        current_date = date.today()
        
    q = query.lower().strip()
    
    if "сегодня" in q:
        return format_schedule(current_date)
    elif "послезавтра" in q:
        return format_schedule(current_date + timedelta(days=2))
    elif "завтра" in q:
        return format_schedule(current_date + timedelta(days=1))
    elif "вчера" in q:
        return format_schedule(current_date - timedelta(days=1))
        
    for i, d in enumerate(DAYS_OF_WEEK):
        if d.lower() in q:
            # Ищем ближайший такой день недели вперед
            curr_weekday = current_date.weekday()
            days_ahead = (i - curr_weekday) % 7
            if days_ahead == 0 and "следующ" in q:
                days_ahead = 7
            target = current_date + timedelta(days=days_ahead)
            return format_schedule(target)
            
    # По умолчанию если ничего не распознано — сегодня
    return format_schedule(current_date)
