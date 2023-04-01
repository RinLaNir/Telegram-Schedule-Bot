import datetime
from xml.etree import ElementTree
from schedule_models import Teacher, Schedule, Subject, LessonType, AuthorizedUser
from typing import List
from config import WEEK_START, SECRET_CODE
import re

def get_week_number(date: datetime.date):
    week_number = date.isocalendar()[1]
    if date.month == 1 and week_number > 50:
        week_number = 0
    return week_number



WEEK_START_NUMBER = get_week_number(WEEK_START)


def get_week_type(date: datetime.date):
    global WEEK_START_NUMBER
    week_number = get_week_number(date)
    week_type = 1 if (week_number - WEEK_START_NUMBER) % 2 else 2
    return week_type


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


def get_or_create_user(user_id, session):
    user = session.query(AuthorizedUser).filter_by(user_id=user_id).first()

    if user is None:
        user = AuthorizedUser(user_id=user_id, is_authorized=0, attempts=0)
        session.add(user)
        session.commit()

    return user


def can_authorize(user: AuthorizedUser):
    assert user.is_authorized == 0
    return user.attempts < 5


def authorize_user(user: AuthorizedUser, secret_code, session):

    if secret_code == SECRET_CODE:
        user.is_authorized = 1
        user.attempts = 0
        session.commit()
        return True
    elif user.is_authorized == 0:
        user.attempts += 1
        session.commit()
    return False

