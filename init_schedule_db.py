from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schedule_models import SheduleBase  # Импортируйте Base из файла models.py

SHEDULE_DATABASE_URL = "sqlite:///shedule.db"  # Здесь укажите путь к вашей базе данных

schedule_engine = create_engine(SHEDULE_DATABASE_URL)
SheduleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=schedule_engine)

def init_schedule_db():
    SheduleBase.metadata.create_all(bind=schedule_engine)