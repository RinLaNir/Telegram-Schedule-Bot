import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode, ContentType
from aiogram.utils import executor
from init_db import SessionLocal
from models import Teacher, Schedule, Subject, LessonType, AuthorizedUser
from config import TOKEN, WEEK_START, SECRET_CODE, ADMINS, PROXY_URL
import re
from functools import wraps
from utils import *


class AuthState(StatesGroup):
    waiting_for_code = State()


logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, proxy=PROXY_URL)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


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
    if message.from_user.id in authorized_users:
        await message.reply("Ви вже авторизовані.")
        return
    await message.reply("Будь ласка, введіть секретний код.")
    await AuthState.waiting_for_code.set()


@dp.message_handler(lambda message: message.text, state=AuthState.waiting_for_code)
async def process_secret_code(message: types.Message, state: FSMContext):
    secret_code = message.text.strip()
    session = SessionLocal()
    user = get_or_create_user(message.from_user.id, session)

    if not can_authorize(user):
        await message.reply("Ви вже використали максимальну кількість спроб авторизації. Будь ласка, зверніться до адміністратора.")
        state.finish()
        return

    if authorize_user(user, secret_code, session):
        await message.reply("Вітаю! Авторизація пройшла успішно.\nСписок доступних команд: /help")
        await state.finish()
    else:
        await message.reply("Неправильний код. Будь ласка, спробуйте ще раз.")


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply('''Ласкаво просимо! Будь ласка, авторизуйтеся через команду /auth, після якої послідує ваш секретний код.
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