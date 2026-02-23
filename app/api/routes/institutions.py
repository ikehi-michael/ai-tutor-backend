"""
Institution routes - School registration, teacher/student management, monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
from app.core.database import get_db
from app.core.security import (
    hash_password,
    create_access_token,
    get_current_user,
    get_current_school_admin,
    get_current_institution_staff,
)
from app.models.user import User, UserRole, UserSubject
from app.models.institution import Institution, TeacherStudent, generate_invite_code
from app.models.question import QuestionHistory, ExamAttempt
from app.schemas.institution import (
    SchoolRegister,
    InstitutionProfile,
    InstitutionUpdate,
    AddTeacherRequest,
    TeacherProfile,
    AddStudentRequest,
    AssignStudentsRequest,
    JoinInstitutionRequest,
    InstitutionStudent,
    InstitutionOverview,
    AssignTopicRequest,
)

router = APIRouter()


# ─── School Registration ─────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_school(data: SchoolRegister, db: Session = Depends(get_db)):
    """Register a new school – creates the Institution + a school-admin user."""

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    if db.query(Institution).filter(Institution.email == data.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A school with this email already exists")

    admin_user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.admin_name,
        role=UserRole.SCHOOL,
        is_active=True,
        subscription_tier="free",
    )
    db.add(admin_user)
    db.flush()

    institution = Institution(
        name=data.school_name,
        address=data.address,
        phone=data.phone,
        email=data.email,
        invite_code=generate_invite_code(),
        admin_id=admin_user.id,
    )
    db.add(institution)
    db.flush()

    admin_user.institution_id = institution.id
    db.commit()
    db.refresh(admin_user)
    db.refresh(institution)

    token = create_access_token(
        data={"sub": str(admin_user.id), "role": admin_user.role.value}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": admin_user.id,
        "role": admin_user.role,
        "institution_id": institution.id,
        "invite_code": institution.invite_code,
    }


# ─── Institution Info ─────────────────────────────────────────────

@router.get("/", response_model=InstitutionProfile)
async def get_institution(
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")

    student_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst.id, User.role == UserRole.STUDENT
    ).scalar() or 0
    teacher_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst.id, User.role == UserRole.TEACHER
    ).scalar() or 0

    return InstitutionProfile(
        id=inst.id,
        name=inst.name,
        address=inst.address,
        phone=inst.phone,
        email=inst.email,
        invite_code=inst.invite_code,
        max_students=inst.max_students,
        max_teachers=inst.max_teachers,
        subscription_tier=inst.subscription_tier,
        is_active=inst.is_active,
        student_count=student_count,
        teacher_count=teacher_count,
        created_at=inst.created_at,
    )


@router.put("/")
async def update_institution(
    data: InstitutionUpdate,
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")

    if data.name is not None:
        inst.name = data.name
    if data.address is not None:
        inst.address = data.address
    if data.phone is not None:
        inst.phone = data.phone

    db.commit()
    db.refresh(inst)
    return {"message": "Institution updated", "name": inst.name}


@router.get("/invite-code")
async def get_invite_code(
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    return {"invite_code": inst.invite_code}


@router.post("/invite-code/regenerate")
async def regenerate_invite_code(
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")
    inst.invite_code = generate_invite_code()
    db.commit()
    db.refresh(inst)
    return {"invite_code": inst.invite_code}


# ─── Teacher Management (school admin only) ──────────────────────

@router.post("/teachers")
async def add_teacher(
    data: AddTeacherRequest,
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")

    teacher_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst.id, User.role == UserRole.TEACHER
    ).scalar() or 0
    if teacher_count >= inst.max_teachers:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Teacher limit reached ({inst.max_teachers})")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        if existing.institution_id == inst.id and existing.role == UserRole.TEACHER:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This teacher is already in your institution")
        if existing.institution_id is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This user already belongs to another institution")
        existing.role = UserRole.TEACHER
        existing.institution_id = inst.id
        db.commit()
        db.refresh(existing)
        return {"message": "Existing user added as teacher", "teacher_id": existing.id}

    if not data.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is required for new teacher accounts")

    teacher = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name or data.email.split("@")[0],
        role=UserRole.TEACHER,
        institution_id=inst.id,
        is_active=True,
        subscription_tier="free",
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return {"message": "Teacher created", "teacher_id": teacher.id}


@router.get("/teachers", response_model=List[TeacherProfile])
async def list_teachers(
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    teachers = db.query(User).filter(
        User.institution_id == current_user.institution_id,
        User.role == UserRole.TEACHER,
    ).all()

    results = []
    for t in teachers:
        sc = db.query(func.count(TeacherStudent.id)).filter(
            TeacherStudent.teacher_id == t.id
        ).scalar() or 0
        results.append(TeacherProfile(
            id=t.id,
            full_name=t.full_name,
            email=t.email,
            student_count=sc,
            created_at=t.created_at,
        ))
    return results


@router.delete("/teachers/{teacher_id}")
async def remove_teacher(
    teacher_id: int,
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    teacher = db.query(User).filter(
        User.id == teacher_id,
        User.institution_id == current_user.institution_id,
        User.role == UserRole.TEACHER,
    ).first()
    if not teacher:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher not found in your institution")

    db.query(TeacherStudent).filter(TeacherStudent.teacher_id == teacher_id).delete()
    teacher.role = UserRole.STUDENT
    teacher.institution_id = None
    db.commit()
    return {"message": "Teacher removed"}


# ─── Student Management (school admin + teachers) ────────────────

@router.post("/students")
async def add_student(
    data: AddStudentRequest,
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Institution not found")

    student_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst.id, User.role == UserRole.STUDENT
    ).scalar() or 0
    if student_count >= inst.max_students:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Student limit reached ({inst.max_students})")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        if existing.institution_id == inst.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Student already in your institution")
        if existing.institution_id is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This user belongs to another institution")
        existing.institution_id = inst.id
        if current_user.role == UserRole.TEACHER:
            link = TeacherStudent(teacher_id=current_user.id, student_id=existing.id)
            db.add(link)
        db.commit()
        return {"message": "Existing student linked to institution", "student_id": existing.id}

    if not data.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is required for new student accounts")

    from app.models.user import StudentClass
    sc = None
    if data.student_class:
        try:
            sc = StudentClass(data.student_class)
        except ValueError:
            pass

    student = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name or data.email.split("@")[0],
        role=UserRole.STUDENT,
        student_class=sc,
        institution_id=inst.id,
        is_active=True,
        subscription_tier="free",
    )
    db.add(student)
    db.flush()

    if current_user.role == UserRole.TEACHER:
        link = TeacherStudent(teacher_id=current_user.id, student_id=student.id)
        db.add(link)

    db.commit()
    db.refresh(student)
    return {"message": "Student created", "student_id": student.id}


@router.get("/students", response_model=List[InstitutionStudent])
async def list_students(
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.SCHOOL:
        students = db.query(User).filter(
            User.institution_id == current_user.institution_id,
            User.role == UserRole.STUDENT,
        ).all()
    else:
        assigned_ids = db.query(TeacherStudent.student_id).filter(
            TeacherStudent.teacher_id == current_user.id
        ).subquery()
        students = db.query(User).filter(User.id.in_(assigned_ids)).all()

    results = []
    for s in students:
        teacher_link = db.query(TeacherStudent).filter(TeacherStudent.student_id == s.id).first()
        teacher_name = None
        if teacher_link:
            teacher = db.query(User).filter(User.id == teacher_link.teacher_id).first()
            teacher_name = teacher.full_name if teacher else None

        results.append(InstitutionStudent(
            id=s.id,
            full_name=s.full_name,
            email=s.email,
            student_class=s.student_class.value if s.student_class else None,
            last_login=s.last_login,
            assigned_teacher=teacher_name,
        ))
    return results


@router.delete("/students/{student_id}")
async def remove_student(
    student_id: int,
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(
        User.id == student_id,
        User.institution_id == current_user.institution_id,
        User.role == UserRole.STUDENT,
    ).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found in your institution")

    db.query(TeacherStudent).filter(TeacherStudent.student_id == student_id).delete()
    student.institution_id = None
    db.commit()
    return {"message": "Student removed from institution"}


@router.post("/students/assign")
async def assign_students_to_teacher(
    data: AssignStudentsRequest,
    current_user: User = Depends(get_current_school_admin),
    db: Session = Depends(get_db),
):
    teacher = db.query(User).filter(
        User.id == data.teacher_id,
        User.institution_id == current_user.institution_id,
        User.role == UserRole.TEACHER,
    ).first()
    if not teacher:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher not found in your institution")

    added = 0
    for sid in data.student_ids:
        student = db.query(User).filter(
            User.id == sid,
            User.institution_id == current_user.institution_id,
            User.role == UserRole.STUDENT,
        ).first()
        if not student:
            continue
        exists = db.query(TeacherStudent).filter(
            TeacherStudent.teacher_id == data.teacher_id,
            TeacherStudent.student_id == sid,
        ).first()
        if not exists:
            db.add(TeacherStudent(teacher_id=data.teacher_id, student_id=sid))
            added += 1

    db.commit()
    return {"message": f"{added} student(s) assigned to teacher"}


@router.post("/join")
async def join_via_invite_code(
    data: JoinInstitutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated student joins an institution via invite code."""
    if current_user.institution_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You already belong to an institution")

    inst = db.query(Institution).filter(
        Institution.invite_code == data.invite_code,
        Institution.is_active == True,
    ).first()
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite code")

    student_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst.id, User.role == UserRole.STUDENT
    ).scalar() or 0
    if student_count >= inst.max_students:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This institution has reached its student limit")

    current_user.institution_id = inst.id
    db.commit()
    return {"message": f"Joined {inst.name}", "institution_id": inst.id}


# ─── Monitoring ───────────────────────────────────────────────────

@router.get("/overview", response_model=InstitutionOverview)
async def institution_overview(
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    inst_id = current_user.institution_id

    if current_user.role == UserRole.SCHOOL:
        student_ids_q = db.query(User.id).filter(
            User.institution_id == inst_id, User.role == UserRole.STUDENT
        )
    else:
        student_ids_q = db.query(TeacherStudent.student_id).filter(
            TeacherStudent.teacher_id == current_user.id
        )

    student_ids = [r[0] for r in student_ids_q.all()]

    total_students = len(student_ids)
    teacher_count = db.query(func.count(User.id)).filter(
        User.institution_id == inst_id, User.role == UserRole.TEACHER
    ).scalar() or 0

    today = datetime.utcnow().date()
    active_today = 0
    if student_ids:
        active_today = db.query(func.count(User.id)).filter(
            User.id.in_(student_ids),
            func.date(User.last_login) == today,
        ).scalar() or 0

    avg_score = 0.0
    total_questions = 0
    if student_ids:
        avg_q = db.query(func.avg(ExamAttempt.score_percentage)).filter(
            ExamAttempt.user_id.in_(student_ids),
            ExamAttempt.completed_at.isnot(None),
        ).scalar()
        avg_score = round(float(avg_q), 2) if avg_q else 0.0

        total_questions = db.query(func.count(QuestionHistory.id)).filter(
            QuestionHistory.user_id.in_(student_ids)
        ).scalar() or 0

    return InstitutionOverview(
        total_students=total_students,
        total_teachers=teacher_count,
        active_today=active_today,
        avg_score=avg_score,
        total_questions_answered=total_questions,
    )


@router.get("/students/{student_id}/progress")
async def student_progress(
    student_id: int,
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")

    if current_user.role == UserRole.SCHOOL:
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Student not in your institution")
    else:
        link = db.query(TeacherStudent).filter(
            TeacherStudent.teacher_id == current_user.id,
            TeacherStudent.student_id == student_id,
        ).first()
        if not link:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Student not assigned to you")

    total_questions = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == student_id
    ).scalar() or 0

    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_questions = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == student_id,
        QuestionHistory.solved_at >= week_ago,
    ).scalar() or 0

    exams = db.query(ExamAttempt).filter(
        ExamAttempt.user_id == student_id,
        ExamAttempt.completed_at.isnot(None),
    ).order_by(ExamAttempt.completed_at.desc()).limit(10).all()

    exam_history = [
        {
            "date": e.completed_at,
            "subject": e.subject,
            "score": e.score_percentage,
        }
        for e in exams
    ]

    subject_stats = []
    for subj in student.subjects:
        acc = 0.0
        if subj.total_questions_attempted > 0:
            acc = round((subj.correct_answers / subj.total_questions_attempted) * 100, 2)
        subject_stats.append({
            "subject": subj.subject_name,
            "accuracy": acc,
            "total_questions": subj.total_questions_attempted,
        })

    return {
        "student": {
            "id": student.id,
            "name": student.full_name,
            "email": student.email,
            "class": student.student_class.value if student.student_class else None,
            "last_login": student.last_login,
        },
        "stats": {
            "total_questions": total_questions,
            "weekly_questions": weekly_questions,
            "total_exams": len(exams),
        },
        "subject_performance": subject_stats,
        "exam_history": exam_history,
    }


# ─── Assignments ──────────────────────────────────────────────────

@router.post("/assignments/topic")
async def assign_topic(
    data: AssignTopicRequest,
    current_user: User = Depends(get_current_institution_staff),
    db: Session = Depends(get_db),
):
    """Placeholder – assign a topic to a set of students."""
    return {
        "message": f"Topic '{data.topic}' ({data.subject}) assigned to {len(data.student_ids)} students",
        "student_ids": data.student_ids,
    }
