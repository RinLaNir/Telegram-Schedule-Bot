from sqlalchemy import Column, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

UserBase = declarative_base()

class AuthorizedUser(UserBase):
    __tablename__ = 'authorized_user'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    is_authorized = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    is_subscribed = Column(Boolean, default=False)