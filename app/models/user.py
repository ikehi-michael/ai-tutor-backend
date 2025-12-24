"""
User database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    """User role types"""
    STUDENT = "student"
    PARENT = "parent"
    ADMIN = "admin"
    SCHOOL = "school"


class StudentClass(str, enum.Enum):
    """Student class levels"""
    SS1 = "SS1"
    SS2 = "SS2"
    SS3 = "SS3"
    JAMB = "JAMB"


class User(Base):
    """User model for students, parents, and admins"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    
    # User type and class
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    student_class = Column(SQLEnum(StudentClass), nullable=True)
    
    # Subscription info
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, default="free")  # free, basic, premium
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Parent-child relationship
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent = relationship("User", remote_side=[id], backref="children")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    subjects = relationship("UserSubject", back_populates="user", cascade="all, delete-orphan")
    questions = relationship("QuestionHistory", back_populates="user", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    exam_attempts = relationship("ExamAttempt", back_populates="user", cascade="all, delete-orphan")
    saved_lessons = relationship("SavedLesson", back_populates="user", cascade="all, delete-orphan")
    lesson_chats = relationship("LessonChat", back_populates="user", cascade="all, delete-orphan")


class UserSubject(Base):
    """Subjects selected by users"""
    __tablename__ = "user_subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_name = Column(String, nullable=False)  # e.g., "Mathematics", "English"
    
    # Performance tracking
    total_questions_attempted = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    user = relationship("User", back_populates="subjects")


