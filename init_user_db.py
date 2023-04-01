from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from user_model import UserBase    # Импортируйте Base из файла models.py

USER_DATABASE_URL = "sqlite:///users.db"  # Здесь укажите путь к вашей базе данных

user_engine = create_engine(USER_DATABASE_URL)
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)

def init_user_db():
    UserBase.metadata.create_all(bind=user_engine)


if __name__ == "__main__":
    init_user_db()