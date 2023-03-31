from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base  # Импортируйте Base из файла models.py

DATABASE_URL = "sqlite:///compmath_bot.db"  # Здесь укажите путь к вашей базе данных

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)