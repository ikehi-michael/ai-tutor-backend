"""
Pydantic schemas for user-related requests and responses
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole, StudentClass


# ===== User Registration & Authentication =====

class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.STUDENT
    student_class: Optional[StudentClass] = None
    subjects: List[str] = []  # List of subject names


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole


# ===== User Profile =====

class UserSubjectResponse(BaseModel):
    """Schema for user subject response"""
    id: int
    subject_name: str
    total_questions_attempted: int
    correct_answers: int
    accuracy: Optional[float] = None
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Schema for user profile response"""
    id: int
    email: str
    phone: Optional[str]
    full_name: str
    role: UserRole
    student_class: Optional[StudentClass]
    subscription_tier: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    subjects: List[UserSubjectResponse] = []
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    student_class: Optional[StudentClass] = None
    subjects: Optional[List[str]] = None


# ===== Parent-Child Linking =====

class LinkChildRequest(BaseModel):
    """Schema for parent linking to child account"""
    child_email: EmailStr
    verification_code: Optional[str] = None  # For security


