import asyncio
import io
import time
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.enums import ParseMode

import config
import database
import ai_agent
import schedule_data
import forum_checker
import file_processor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация Telegram Бота и Диспетчера
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# --- Вспомогательные функции ---

async def check_and_notify_complaints(chat_id: int, is_auto_check: bool = False):
    """Проверяет форум Majestic RP на жалобы и отправляет уведомление, если найдены новые"""
    try:
        new_complaints = await forum_checker.check_new_complaints(auto_mark_seen=True)
        if new_complaints:
            alert_text = forum_checker.format_complaints_alert(new_complaints)
            if is_auto_check:
                alert_text = "🔔 <b>[Фоновая проверка раз в 2 часа]</b>\n" + alert_text
            await bot.send_message(chat_id, alert_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            return True
    except Exception as e:
        logger.error(f"Ошибка проверки жалоб: {e}")
    return False

def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для быстрого просмотра расписания"""
    kb = [
        [
            InlineKeyboardButton(text="Сегодня", callback_data="sched_today"),
            InlineKeyboardButton(text="Завтра", callback_data="sched_tomorrow"),
        ],
        [
            InlineKeyboardButton(text="Понедельник", callback_data="sched_mon"),
            InlineKeyboardButton(text="Вторник", callback_data="sched_tue"),
            InlineKeyboardButton(text="Среда", callback_data="sched_wed"),
        ],
        [
            InlineKeyboardButton(text="Четверг", callback_data="sched_thu"),
            InlineKeyboardButton(text="Пятница", callback_data="sched_fri"),
            InlineKeyboardButton(text="Суббота", callback_data="sched_sat"),
        ],
        [
            InlineKeyboardButton(text="Какая сейчас неделя?", callback_data="sched_week_type")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- Команды бота ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Обновляем активность
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    
    # Проверяем жалобы при входе
    await check_and_notify_complaints(message.chat.id)
    
    week_type = schedule_data.get_week_type()
    welcome_text = (
        f"✨ <b>Приветствую, {config.MAJESTIC_NICKNAME}!</b>\n\n"
        f"Меня зовут <b>Селеста (Selesta)</b>. Я твоя персональная ИИ-помощница с постоянной памятью, доступом в интернет и полным набором инструментов:\n\n"
        f"📚 <b>Расписание группы П1-25В</b>:\n"
        f"• Сейчас идет неделя: <b>{week_type.upper()}</b>\n"
        f"• Спрашивай в любой удобной форме: <i>«Какое расписание на завтра?»</i>, <i>«Что в четверг?»</i>, <i>«Какие пары сегодня?»</i>.\n\n"
        f"🛡️ <b>Majestic RP Memphis</b>:\n"
        f"• Я автоматически отслеживаю новые жалобы на тебя на форуме при каждом твоем сообщении.\n"
        f"• Если ты не пишешь мне более 2 часов, я сама тихо проверю форум и пришлю алерт, если кто-то подаст жалобу.\n\n"
        f"📁 <b>Документы и фото</b>:\n"
        f"• Отправляй мне фотографии, скриншоты, файлы PDF, Word (DOCX), код или текст — я всё внимательно изучу и помогу.\n\n"
        f"🌐 <b>Интернет и память</b>:\n"
        f"• Я помню факты о тебе, могу искать свежую информацию в сети и запоминать то, что ты мне доверишь.\n\n"
        f"Используй кнопки ниже или просто напиши мне любой вопрос!"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=get_schedule_keyboard())

@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    await message.answer("📅 Выберите день для просмотра расписания группы П1-25В:", reply_markup=get_schedule_keyboard())

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    """Ручная проверка жалоб на форуме Majestic RP"""
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    
    wait_msg = await message.answer("🔍 Проверяю форум Majestic RP Memphis на наличие жалоб...")
    new_complaints = await forum_checker.check_new_complaints(auto_mark_seen=True)
    
    await wait_msg.delete()
    if new_complaints:
        alert = forum_checker.format_complaints_alert(new_complaints)
        await message.answer(alert, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await message.answer(
            f"✅ <b>Всё чисто!</b>\nНовых нерассмотренных жалоб на администратора <b>{config.MAJESTIC_NICKNAME}</b> на форуме нет.",
            parse_mode=ParseMode.HTML
        )

@dp.message(Command("memory"))
async def cmd_memory(message: types.Message):
    """Показывает, что агент помнит о пользователе"""
    facts = database.get_all_user_facts()
    if not facts:
        await message.answer("Память пока пуста.")
        return
    text = "🧠 <b>Моя долговременная память о тебе:</b>\n\n"
    for k, v in facts.items():
        text += f"• <b>{k}</b>: {v}\n"
    text += "\n<i>Ты можешь попросить меня запомнить что-то новое прямо в диалоге!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Очищает контекст текущей беседы"""
    database.clear_chat_history(message.chat.id)
    await message.answer("🧹 Контекст диалога очищен! (Долговременные факты о тебе сохранены).")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 <b>Команды бота:</b>\n\n"
        "• /schedule — Кнопки быстрого просмотра расписания\n"
        "• /check — Проверить жалобы на Majestic RP прямо сейчас\n"
        "• /memory — Посмотреть сохраненную память о тебе\n"
        "• /clear — Сбросить контекст диалога\n"
        "• /help — Это справочное сообщение\n\n"
        "💬 Ты можешь общаться со мной голосом или текстом на любые темы, присылать файлы, документы, фото и таблицы!"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# --- Обработка нажатий на инлайн кнопки расписания ---

@dp.callback_query(F.data.startswith("sched_"))
async def handle_schedule_callback(callback: types.CallbackQuery):
    action = callback.data
    database.set_state("last_user_activity", time.time())
    
    if action == "sched_today":
        text = schedule_data.get_schedule_by_relative_query("сегодня")
    elif action == "sched_tomorrow":
        text = schedule_data.get_schedule_by_relative_query("завтра")
    elif action == "sched_mon":
        text = schedule_data.get_schedule_by_relative_query("понедельник")
    elif action == "sched_tue":
        text = schedule_data.get_schedule_by_relative_query("вторник")
    elif action == "sched_wed":
        text = schedule_data.get_schedule_by_relative_query("среда")
    elif action == "sched_thu":
        text = schedule_data.get_schedule_by_relative_query("четверг")
    elif action == "sched_fri":
        text = schedule_data.get_schedule_by_relative_query("пятница")
    elif action == "sched_sat":
        text = schedule_data.get_schedule_by_relative_query("суббота")
    elif action == "sched_week_type":
        wt = schedule_data.get_week_type()
        text = f"🔄 <b>Сейчас идет неделя: {wt.upper()}</b>\n(Расписание автоматически подстраивается под эту неделю)."
    else:
        text = "Неизвестное действие."
        
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

# --- Обработка фотографий ---

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    # Обновляем время активности пользователя
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    
    # 1. При каждом запросе проверяем жалобы на Majestic RP
    await check_and_notify_complaints(message.chat.id)
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Скачиваем самое качественное фото (последнее в списке)
    photo = message.photo[-1]
    file_io = io.BytesIO()
    await bot.download(photo, destination=file_io)
    file_bytes = file_io.getvalue()
    
    # Обрабатываем через file_processor
    caption = message.caption or "Посмотри на изображение и проанализируй его."
    desc, image_url = file_processor.process_telegram_file(file_bytes, "photo.jpg", "image/jpeg")
    
    # Запрос к ИИ агенту с изображением
    reply = await ai_agent.ask_agent(message.chat.id, caption, image_url=image_url)
    await message.answer(reply, parse_mode=ParseMode.HTML)

# --- Обработка документов и файлов ---

@dp.message(F.document)
async def handle_document(message: types.Message):
    # Обновляем время активности
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    
    # Проверяем жалобы при каждом запросе
    await check_and_notify_complaints(message.chat.id)
    
    await bot.send_chat_action(message.chat.id, "typing")
    
    doc = message.document
    file_io = io.BytesIO()
    await bot.download(doc, destination=file_io)
    file_bytes = file_io.getvalue()
    
    extracted_text, image_url = file_processor.process_telegram_file(
        file_bytes,
        doc.file_name or "document",
        doc.mime_type or ""
    )
    
    caption = message.caption or ""
    full_prompt = f"{caption}\n\n{extracted_text}".strip()
    
    reply = await ai_agent.ask_agent(message.chat.id, full_prompt, image_url=image_url)
    await message.answer(reply, parse_mode=ParseMode.HTML)

# --- Обработка обычных текстовых сообщений ---

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    # Обновляем время активности
    database.set_state("last_user_activity", time.time())
    database.set_state("last_chat_id", message.chat.id)
    
    # Проверяем жалобы на Majestic RP при каждом запросе
    await check_and_notify_complaints(message.chat.id)
    
    user_text = message.text.strip()
    
    # Индикатор набора текста
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Запрос к ИИ агенту
    reply = await ai_agent.ask_agent(message.chat.id, user_text)
    
    # Если ответ слишком длинный для одного сообщения в Telegram (лимит 4096 символов)
    if len(reply) > 4000:
        chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for chunk in chunks:
            await message.answer(chunk, parse_mode=ParseMode.HTML)
    else:
        await message.answer(reply, parse_mode=ParseMode.HTML)

# --- Фоновая задача: проверка жалоб каждые 2 часа, если пользователь не пишет ---

async def background_complaint_monitor():
    """
    Фоновый цикл проверки жалоб на форуме Majestic RP раз в 2 часа,
    если пользователь в это время не взаимодействует с ботом.
    """
    CHECK_INTERVAL_SECONDS = 300  # проверяем таймер каждые 5 минут
    IDLE_THRESHOLD_SECONDS = 2 * 3600  # 2 часа бездействия
    
    logger.info("Фоновый мониторинг жалоб запущен.")
    
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            
            now = time.time()
            last_activity = database.get_state("last_user_activity", 0.0)
            last_bg_check = database.get_state("last_bg_check", 0.0)
            
            # Проверяем условие: прошло ли 2 часа с последней активности пользователя
            # И прошло ли 2 часа с момента последней фоновой проверки
            user_idle = (now - last_activity) >= IDLE_THRESHOLD_SECONDS
            check_due = (now - last_bg_check) >= IDLE_THRESHOLD_SECONDS
            
            if user_idle and check_due:
                database.set_state("last_bg_check", now)
                chat_id = config.TELEGRAM_ADMIN_ID or database.get_state("last_chat_id", None)
                
                if chat_id:
                    logger.info(f"Запуск фоновой проверки жалоб (прошло 2 часа неактивности)...")
                    await check_and_notify_complaints(chat_id, is_auto_check=True)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Ошибка в фоновом мониторинге жалоб: {e}")

# --- Главная функция запуска бота ---

async def main():
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "ВАШ_ТОКЕН_ТЕЛЕГРАМ_БОТА":
        logger.error("❌ Токен бота не указан! Откройте файл .env и укажите TELEGRAM_BOT_TOKEN.")
        print("\n" + "="*60)
        print("ВНИМАНИЕ: Укажите TELEGRAM_BOT_TOKEN и PLUSVIBE_API_KEY в файле .env")
        print("="*60 + "\n")
        return

    logger.info(f"Запуск ИИ-агента для {config.MAJESTIC_NICKNAME}...")
    
    # Запускаем фоновую задачу мониторинга
    bg_task = asyncio.create_task(background_complaint_monitor())
    
    try:
        # Удаляем вебхуки и запускаем поллинг
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        bg_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
