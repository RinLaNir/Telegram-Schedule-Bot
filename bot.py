import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from init_db import SessionLocal
from xml.etree import ElementTree
from models import Teacher, Schedule, Subject, LessonType, AuthorizedUser
from config import TOKEN, WEEK_START, SECRET_CODE, ADMINS
import datetime
from typing import List
import re
from functools import wraps

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

authorized_users = set()

def get_week_number(date: datetime.date):
    week_number = date.isocalendar()[1]
    if date.month == 1 and week_number > 50:
        week_number = 0
    return week_number

WEEK_START_NUMBER = get_week_number(WEEK_START)

def parse_teacher_contacts(contacts_str: str):
    if not contacts_str or not contacts_str.strip():
        return None, None, None, None

    try:
        contacts_xml = ElementTree.fromstring(contacts_str)
    except ElementTree.ParseError:
        return None, None, None, None

    phone = contacts_xml.findtext("phone", default=None)
    email = ', '.join([e.text for e in contacts_xml.findall("email") if e.text]) or None
    telegram = contacts_xml.findtext("telegram", default=None)
    viber = contacts_xml.findtext("viber", default=None)

    return phone, email, telegram, viber

def get_week_type(date: datetime.date):
    week_number = get_week_number(date)
    week_type = 1 if (week_number - WEEK_START_NUMBER) % 2 else 2
    return week_type

def format_schedule_for_day(schedule: List[Schedule]) -> str:
    schedule_str = ""

    if schedule:
        for lesson in schedule:
            clock_emoji = "🕒"
            schedule_str += f"{clock_emoji} <b>{lesson.time}</b> | <b>{lesson.subject.name}</b> ({lesson.lesson_type.name})"
            if lesson.teacher:
                schedule_str += f", {lesson.teacher.name}"
            
            if lesson.location:
                if re.match(r"^https?://", lesson.location):
                    schedule_str += f', <a href="{lesson.location}">Онлайн</a>'
                else:
                    schedule_str += f", ауд. {lesson.location}"
            schedule_str += "\n"
    
    return schedule_str

def format_schedule(schedule: List[Schedule], week_type: int) -> str:
    weekdays = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота"]
    schedule_str = ""

    for day, weekday in enumerate(weekdays, start=1):
        lessons_for_day = [lesson for lesson in schedule if lesson.day_of_week == day and (lesson.week_type == week_type or lesson.week_type == 0)]

        if lessons_for_day: 
            schedule_str += f"<b>{weekday}</b>:\n"
        schedule_str += format_schedule_for_day(lessons_for_day)
        schedule_str += "\n"

    return schedule_str

def load_authorized_users(session):
    authorized_users = session.query(AuthorizedUser).filter(AuthorizedUser.is_authorized == 1).all()
    return {user.user_id for user in authorized_users}

def authorize_user(user_id, secret_code, session):
    user = session.query(AuthorizedUser).filter_by(user_id=user_id).first()

    if user is None:
        user = AuthorizedUser(user_id=user_id, is_authorized=0, attempts=0)
        session.add(user)

    if secret_code == SECRET_CODE:
        user.is_authorized = 1
        user.attempts = 0
        session.commit()
        authorized_users.add(user_id)
        return True
    elif user.is_authorized == 0:
        user.attempts += 1
        session.commit()
        return False

def check_authorization(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in authorized_users:
            await message.reply("Необхідно ввести секретний код для доступу до команд.")
            return
        return await func(message, *args, **kwargs)
    return wrapper

@dp.message_handler(commands=["reset_attempts"])
async def cmd_reset_attempts(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    user_id = int(message.get_args())
    with SessionLocal() as session:
        authorized_user = session.query(AuthorizedUser).filter_by(user_id=user_id).first()
        if authorized_user:
            authorized_user.attempts = 0
            session.commit()
            await message.reply(f"Счетчик попыток для пользователя {user_id} успешно сброшен.")
        else:
            await message.reply(f"Пользователь с ID {user_id} не найден в базе данных.")

@dp.message_handler(commands=["auth"])
async def cmd_auth(message: types.Message):
    secret_code = message.text.split(' ')[1] if len(message.text.split(' ')) > 1 else ''
    session = SessionLocal()
    user_id = message.from_user.id

    if not secret_code:
        await message.reply("Будь ласка, введіть секретний код після команди.")
        return

    if authorize_user(user_id, secret_code, session):
        await message.reply("Вітаю! Авторизація пройшла успішно.\nСписок доступних команд: /help")
    else:
        await message.reply("Неправильний код. Будь ласка, спробуйте ще раз.")

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply('''Ласкаво просимо! Будь ласка, авторизуйтеся, введіть команду /auth, після якої слідує ваш секретний код.

Приклад: /auth 12345
Список доступних команд: /help
''')

@dp.message_handler(commands=["help"])
@check_authorization
async def cmd_help(message: types.Message):
    await message.reply('''Доступні команди:

/teachers - Список викладачів
/schedule - Розклад занять
/today - Розклад на сьогодні
/tomorrow - Розклад на завтра
/week_type - Повертає, який тиждень зараз - парний чи непарний
''')
    
@dp.message_handler(commands=["teachers"])
@check_authorization
async def cmd_teachers(message: types.Message):
    session = SessionLocal()

    teachers = session.query(Teacher).all()
    response = "<b>Контакти викладачів:</b>\n\n"

    for teacher in teachers:
        phone, email, telegram, viber = parse_teacher_contacts(teacher.contacts)

        if phone or email or telegram or viber:
            response += f"<b>{teacher.name}</b>\n"
            if phone:
                response += f"Телефон: {phone}\n"
            if email:
                response += f"Email: {email}\n"
            if telegram:
                response += f"Телеграм: {telegram}\n"
            if viber:
                response += f"Viber: {viber}\n"
        response += "\n"

    session.close()

    await message.reply(response, parse_mode=ParseMode.HTML)

@dp.message_handler(commands=["week_type"])
@check_authorization
async def cmd_week_type(message: types.Message):
    week_type = get_week_type(datetime.date.today())
    response = "Зараз "
    response += f"парний" if week_type == 1 else f"непарний"
    response += " тиждень"
    await message.reply(response, parse_mode=ParseMode.HTML)

@dp.message_handler(commands=["schedule"])
@check_authorization
async def cmd_schedule(message: types.Message):
    session = SessionLocal()

    week_type = get_week_type(datetime.date.today())
    schedule = session.query(Schedule).join(Subject).join(LessonType).join(Teacher, isouter=True).order_by(Schedule.day_of_week, Schedule.time).all()

    response = format_schedule(schedule, week_type)
    session.close()

    await message.reply(response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def handle_schedule_by_day(message: types.Message, days_offset: int):
    session = SessionLocal()
    target_day = datetime.date.today() + datetime.timedelta(days=days_offset)
    week_type = get_week_type(target_day)
    day_of_week = target_day.weekday() + 1
    message_string = "<b>Пари сьогодні:</b>\n\n" if days_offset == 0 else "<b>Пари завтра:</b>\n\n"

    schedule = session.query(Schedule).join(Subject).join(LessonType).join(Teacher, 
    isouter=True).filter((Schedule.day_of_week == day_of_week) & ((Schedule.week_type == week_type) | (Schedule.week_type == 0))).order_by(Schedule.time).all()
    
    response = format_schedule_for_day(schedule)

    if not response.strip():
        message_string = "Сьогодні вільний день" if days_offset == 0 else "Завтра вільний день"
    else:
        message_string += response    

    session.close()
    await message.reply(message_string, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@dp.message_handler(commands=["today"])
@check_authorization
async def cmd_today(message: types.Message):
    await handle_schedule_by_day(message, days_offset=0)

@dp.message_handler(commands=["tomorrow"])
@check_authorization
async def cmd_tomorrow(message: types.Message):
    await handle_schedule_by_day(message, days_offset=1)



if __name__ == "__main__":
    with SessionLocal() as session:
        authorized_users = load_authorized_users(session)
    
    executor.start_polling(dp, skip_updates=True)