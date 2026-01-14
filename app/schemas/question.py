"""
Pydantic schemas for question-related requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ===== Question Solving =====

class QuestionSolveRequest(BaseModel):
    """Schema for solving a question"""
    question_text: Optional[str] = None
    question_image: Optional[str] = None  # Base64 encoded image or URL
    subject: Optional[str] = None  # Optional hint


class SolutionStep(BaseModel):
    """Individual step in solution"""
    step_number: int
    description: str
    formula: Optional[str] = None
    explanation: str


class QuestionSolveResponse(BaseModel):
    """Schema for question solution response"""
    question_id: int
    question_text: str
    subject: str
    topic: str
    solution: str
    steps: List[SolutionStep]
    related_topics: List[str]
    similar_questions: Optional[List[str]] = []
    

class QuestionHistoryResponse(BaseModel):
    """Schema for question history"""
    id: int
    question_text: str
    subject: Optional[str]
    topic: Optional[str]
    ai_solution: str
    solved_at: datetime
    
    class Config:
        from_attributes = True


# ===== Study Plans =====

class StudyPlanRequest(BaseModel):
    """Schema for creating a study plan"""
    target_exam: str = Field(..., description="WAEC, JAMB, or NECO")
    exam_date: Optional[datetime] = None
    hours_per_day: int = Field(..., ge=1, le=12)
    days_per_week: int = Field(..., ge=1, le=7)
    subjects: List[str]
    weak_areas: Optional[List[str]] = []


class DailySchedule(BaseModel):
    """Daily schedule item"""
    day: str
    time_slot: str
    subject: str
    topic: str
    duration_minutes: int
    activity_type: str  # "study", "practice", "review"


class StudyPlanResponse(BaseModel):
    """Schema for study plan response"""
    id: int
    plan_name: str
    target_exam: str
    exam_date: Optional[datetime]
    hours_per_day: int
    days_per_week: int
    weekly_schedule: List[DailySchedule]
    completion_percentage: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== Mock Exams =====

class ExamQuestion(BaseModel):
    """Individual exam question"""
    question_number: int
    question_text: str
    options: Dict[str, str]  # {"A": "option1", "B": "option2", ...}
    correct_answer: Optional[str] = None  # Hidden until submission


class MockExamRequest(BaseModel):
    """Schema for creating a mock exam"""
    exam_type: str  # "WAEC", "JAMB", "practice"
    subject: str
    year: Optional[str] = None  # Specific year or "random"
    number_of_questions: int = Field(default=40, ge=10, le=100)
    time_limit_minutes: int = Field(default=60, ge=15, le=180)


class MockExamResponse(BaseModel):
    """Schema for mock exam response"""
    exam_id: int
    exam_type: str
    subject: str
    total_questions: int
    time_limit_minutes: int
    questions: List[ExamQuestion]
    started_at: datetime


class ExamSubmissionRequest(BaseModel):
    """Schema for submitting exam answers"""
    exam_id: int
    answers: Dict[int, str]  # {question_number: selected_answer}
    time_taken_seconds: int


class ExamResultResponse(BaseModel):
    """Schema for exam results"""
    exam_id: int
    total_questions: int
    correct_count: int
    score_percentage: int
    time_taken_seconds: int
    weak_topics: List[str]
    detailed_results: List[Dict]  # Question-by-question breakdown
    recommendations: List[str]
    
    class Config:
        from_attributes = True


# ===== Topic Teaching =====

class TopicTeachRequest(BaseModel):
    """Schema for requesting topic explanation"""
    subject: str
    topic: str
    difficulty_level: Optional[str] = "medium"  # "simple", "medium", "advanced"


class TopicTeachResponse(BaseModel):
    """Schema for topic teaching response"""
    subject: str
    topic: str
    summary: str
    detailed_explanation: str
    examples: List[str]
    practice_questions: List[str]
    video_link: Optional[str] = None  # YouTube link if available
    youtube_video_id: Optional[str] = None  # YouTube video ID for embedding
    lesson_id: Optional[int] = None  # ID of saved lesson for chat


# ===== Saved Lessons =====

class SavedLessonResponse(BaseModel):
    """Schema for saved lesson response"""
    id: int
    subject: str
    topic: str
    difficulty_level: Optional[str]
    lesson_data: Dict
    youtube_video_id: Optional[str]
    youtube_video_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    last_accessed_at: datetime
    
    class Config:
        from_attributes = True


# ===== Lesson Chat =====

class LessonChatMessage(BaseModel):
    """Schema for a chat message"""
    role: str  # "user" or "assistant"
    message: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LessonChatRequest(BaseModel):
    """Schema for sending a chat message"""
    lesson_id: int
    message: str


class LessonChatResponse(BaseModel):
    """Schema for chat response"""
    message: str


# ===== Past Questions =====

class PastQuestionResponse(BaseModel):
    """Schema for past question response"""
    id: int
    exam_type: str
    subject: str
    year: str
    question_number: int
    question_text: str
    options: Dict[str, str]
    correct_answer: str
    topic: Optional[str]
    source_pdf: Optional[str]
    page_number: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PastQuestionUpload(BaseModel):
    """Schema for past question upload request"""
    exam_type: str
    subject: str
    year: str


class AvailablePastQuestionsResponse(BaseModel):
    """Schema for available past questions list"""
    exam_type: str
    subject: str
    year: str
    question_count: int

