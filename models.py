from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    contacts = Column(String)

class LessonType(Base):
    __tablename__ = 'lesson_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True)
    day_of_week = Column(Integer, nullable=False)
    time = Column(String, nullable=False)
    week_type = Column(Integer, nullable=False, default=0)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    lesson_type_id = Column(Integer, ForeignKey('lesson_types.id'))
    location = Column(String, nullable=True)

    lesson_type = relationship("LessonType", back_populates="schedules")
    subject = relationship("Subject", back_populates="schedules")
    teacher = relationship("Teacher", back_populates="schedules")
    
    __table_args__ = (UniqueConstraint('day_of_week', 'time', 'week_type', name='uq_schedule_day_time_week_type'), )

class AuthorizedUser(Base):
    __tablename__ = 'authorized_user'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    is_authorized = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)

LessonType.schedules = relationship("Schedule", order_by=Schedule.id, back_populates="lesson_type")
Subject.schedules = relationship("Schedule", order_by=Schedule.id, back_populates="subject")
Teacher.schedules = relationship("Schedule", order_by=Schedule.id, back_populates="teacher")