"""
Question history and exam models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class QuestionHistory(Base):
    """History of questions asked by students"""
    __tablename__ = "question_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Question data
    question_text = Column(Text, nullable=False)
    question_image_url = Column(String, nullable=True)  # If uploaded as image
    
    # Subject/Topic mapping
    subject = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    
    # AI Response
    ai_solution = Column(Text, nullable=False)
    steps = Column(JSON, nullable=True)  # Step-by-step solution as JSON
    related_topics = Column(JSON, nullable=True)  # List of related topics
    
    # Metadata
    solved_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    user = relationship("User", back_populates="questions")


class StudyPlan(Base):
    """Personalized study plans for students"""
    __tablename__ = "study_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Plan details
    plan_name = Column(String, nullable=False)
    target_exam = Column(String, nullable=False)  # "WAEC", "JAMB", etc.
    exam_date = Column(DateTime, nullable=True)
    
    # Time allocation
    hours_per_day = Column(Integer, nullable=False)
    days_per_week = Column(Integer, nullable=False)
    
    # Plan structure (JSON)
    weekly_schedule = Column(JSON, nullable=False)  # Detailed weekly breakdown
    
    # Progress
    is_active = Column(Boolean, default=True)
    completion_percentage = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    user = relationship("User", back_populates="study_plans")


class ExamAttempt(Base):
    """Mock exam attempts and results"""
    __tablename__ = "exam_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Exam configuration
    exam_type = Column(String, nullable=False)  # "WAEC", "JAMB", "practice"
    subject = Column(String, nullable=False)
    year = Column(String, nullable=True)  # "2023", "2022", or "random"
    
    # Questions and answers (JSON)
    questions = Column(JSON, nullable=False)  # List of questions
    user_answers = Column(JSON, nullable=False)  # User's answers
    correct_answers = Column(JSON, nullable=False)  # Correct answers
    
    # Timing
    time_limit_minutes = Column(Integer, nullable=False)
    time_taken_seconds = Column(Integer, nullable=False)
    
    # Results
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    score_percentage = Column(Integer, nullable=False)
    
    # Weak areas identified
    weak_topics = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    user = relationship("User", back_populates="exam_attempts")


class SavedLesson(Base):
    """Saved lessons for users"""
    __tablename__ = "saved_lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Lesson identification
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    difficulty_level = Column(String, nullable=True)  # "simple", "medium", "advanced"
    
    # Lesson content (JSON)
    lesson_data = Column(JSON, nullable=False)  # Full lesson content from AI
    
    # YouTube video
    youtube_video_id = Column(String, nullable=True)  # Video ID for embedding
    youtube_video_url = Column(String, nullable=True)  # Full YouTube URL
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    user = relationship("User", back_populates="saved_lessons")
    chat_messages = relationship("LessonChat", back_populates="lesson", cascade="all, delete-orphan")


class LessonChat(Base):
    """Chat messages for topic-specific conversations"""
    __tablename__ = "lesson_chat"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("saved_lessons.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    lesson = relationship("SavedLesson", back_populates="chat_messages")
    user = relationship("User", back_populates="lesson_chats")


