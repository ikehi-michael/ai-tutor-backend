"""
Institution and teacher-student relationship models
"""
import secrets
import string
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


def generate_invite_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part1 = "STEM"
    part2 = "".join(secrets.choice(chars) for _ in range(4))
    part3 = "".join(secrets.choice(chars) for _ in range(4))
    return f"{part1}-{part2}-{part3}"


class Institution(Base):
    """School / institution that manages teachers and students"""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    invite_code = Column(String, unique=True, nullable=False, index=True, default=generate_invite_code)

    max_students = Column(Integer, default=100)
    max_teachers = Column(Integer, default=10)
    subscription_tier = Column(String, default="free")
    is_active = Column(Boolean, default=True)

    # The school-admin user who created this institution
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # All users (school admin, teachers, students) linked to this institution
    users = relationship("User", back_populates="institution", foreign_keys="[User.institution_id]")


class TeacherStudent(Base):
    """Many-to-many link between teachers and students within an institution"""
    __tablename__ = "teacher_students"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
