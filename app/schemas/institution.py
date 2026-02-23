"""
Pydantic schemas for institution-related requests and responses
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ===== School Registration =====

class SchoolRegister(BaseModel):
    school_name: str = Field(..., min_length=2)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=8)
    admin_name: str = Field(..., min_length=2)


# ===== Institution Info =====

class InstitutionProfile(BaseModel):
    id: int
    name: str
    address: Optional[str]
    phone: Optional[str]
    email: str
    invite_code: str
    max_students: int
    max_teachers: int
    subscription_tier: str
    is_active: bool
    student_count: int = 0
    teacher_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


# ===== Teacher Management =====

class AddTeacherRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class TeacherProfile(BaseModel):
    id: int
    full_name: str
    email: str
    student_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== Student Management =====

class AddStudentRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    student_class: Optional[str] = None


class AssignStudentsRequest(BaseModel):
    teacher_id: int
    student_ids: List[int]


class JoinInstitutionRequest(BaseModel):
    invite_code: str


class InstitutionStudent(BaseModel):
    id: int
    full_name: str
    email: str
    student_class: Optional[str] = None
    last_login: Optional[datetime] = None
    assigned_teacher: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Monitoring =====

class InstitutionOverview(BaseModel):
    total_students: int = 0
    total_teachers: int = 0
    active_today: int = 0
    avg_score: float = 0
    total_questions_answered: int = 0


# ===== Assignments =====

class AssignTopicRequest(BaseModel):
    student_ids: List[int]
    subject: str
    topic: str
    due_date: Optional[datetime] = None


class AssignStudyPlanRequest(BaseModel):
    student_ids: List[int]
    plan_name: str
    subjects: List[str]
    due_date: Optional[datetime] = None
