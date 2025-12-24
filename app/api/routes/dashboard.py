"""
Dashboard routes - Analytics and progress tracking
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict
from app.core.database import get_db
from app.core.security import get_current_user, get_current_parent
from app.models.user import User, UserSubject, UserRole
from app.models.question import QuestionHistory, ExamAttempt, StudyPlan
from app.schemas.user import LinkChildRequest

router = APIRouter()


@router.get("/student/overview")
async def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student dashboard overview with key statistics
    """
    # Total questions solved
    total_questions = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == current_user.id
    ).scalar()
    
    # Questions solved today
    today = datetime.utcnow().date()
    questions_today = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == current_user.id,
        func.date(QuestionHistory.solved_at) == today
    ).scalar()
    
    # This week
    week_ago = datetime.utcnow() - timedelta(days=7)
    questions_this_week = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == current_user.id,
        QuestionHistory.solved_at >= week_ago
    ).scalar()
    
    # Exam attempts
    total_exams = db.query(func.count(ExamAttempt.id)).filter(
        ExamAttempt.user_id == current_user.id,
        ExamAttempt.completed_at.isnot(None)
    ).scalar()
    
    # Average exam score
    avg_score = db.query(func.avg(ExamAttempt.score_percentage)).filter(
        ExamAttempt.user_id == current_user.id,
        ExamAttempt.completed_at.isnot(None)
    ).scalar()
    
    # Subject performance
    subject_stats = []
    for subject in current_user.subjects:
        accuracy = None
        if subject.total_questions_attempted > 0:
            accuracy = (subject.correct_answers / subject.total_questions_attempted) * 100
        
        subject_stats.append({
            "subject": subject.subject_name,
            "questions_attempted": subject.total_questions_attempted,
            "accuracy": round(accuracy, 2) if accuracy else 0
        })
    
    # Sort by accuracy (worst first for identifying weak areas)
    subject_stats.sort(key=lambda x: x["accuracy"])
    
    # Determine weakest subject - only consider subjects with at least 5 questions attempted
    # This ensures we're identifying actual weak areas, not subjects that haven't been tested yet
    weakest_subject = None
    subjects_with_sufficient_data = [
        s for s in subject_stats 
        if s["questions_attempted"] >= 5
    ]
    if subjects_with_sufficient_data:
        weakest_subject = subjects_with_sufficient_data[0]["subject"]
    
    # Active study plan
    active_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == current_user.id,
        StudyPlan.is_active == True
    ).first()
    
    # Study streak (consecutive days with activity)
    streak = calculate_study_streak(current_user.id, db)
    
    return {
        "user": {
            "name": current_user.full_name,
            "class": current_user.student_class,
            "subscription": current_user.subscription_tier
        },
        "stats": {
            "total_questions_solved": total_questions or 0,
            "questions_today": questions_today or 0,
            "questions_this_week": questions_this_week or 0,
            "total_exams_taken": total_exams or 0,
            "average_exam_score": round(avg_score, 2) if avg_score else 0,
            "study_streak_days": streak
        },
        "subject_performance": subject_stats,
        "weakest_subject": weakest_subject,
        "active_study_plan": {
            "id": active_plan.id,
            "name": active_plan.plan_name,
            "completion": active_plan.completion_percentage,
            "exam_date": active_plan.exam_date
        } if active_plan else None
    }


@router.get("/student/progress-chart")
async def get_progress_chart(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily activity data for progress chart
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Questions per day
    questions_by_day = db.query(
        func.date(QuestionHistory.solved_at).label('date'),
        func.count(QuestionHistory.id).label('count')
    ).filter(
        QuestionHistory.user_id == current_user.id,
        QuestionHistory.solved_at >= cutoff_date
    ).group_by(func.date(QuestionHistory.solved_at)).all()
    
    # Format data
    chart_data = []
    for date, count in questions_by_day:
        chart_data.append({
            "date": str(date),
            "questions_solved": count
        })
    
    return {
        "period_days": days,
        "data": chart_data
    }


@router.get("/parent/children")
async def get_parent_dashboard(
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Parent dashboard - view all children's progress
    """
    children = db.query(User).filter(User.parent_id == current_user.id).all()
    
    if not children:
        return {
            "message": "No linked children found",
            "children": []
        }
    
    children_data = []
    for child in children:
        # Get child's stats
        total_questions = db.query(func.count(QuestionHistory.id)).filter(
            QuestionHistory.user_id == child.id
        ).scalar()
        
        # Recent exam scores
        recent_exams = db.query(ExamAttempt).filter(
            ExamAttempt.user_id == child.id,
            ExamAttempt.completed_at.isnot(None)
        ).order_by(ExamAttempt.completed_at.desc()).limit(5).all()
        
        exam_scores = [exam.score_percentage for exam in recent_exams]
        
        # Subject performance - get all subjects with accuracy
        all_subjects = []
        weak_subjects = []
        for subject in child.subjects:
            if subject.total_questions_attempted > 0:
                accuracy = (subject.correct_answers / subject.total_questions_attempted) * 100
                all_subjects.append({
                    "subject": subject.subject_name,
                    "accuracy": round(accuracy, 2),
                    "total_questions": subject.total_questions_attempted,
                    "correct_answers": subject.correct_answers
                })
                if accuracy < 60:
                    weak_subjects.append({
                        "subject": subject.subject_name,
                        "accuracy": round(accuracy, 2)
                    })
        
        # Study time (estimated from questions)
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_questions = db.query(func.count(QuestionHistory.id)).filter(
            QuestionHistory.user_id == child.id,
            QuestionHistory.solved_at >= week_ago
        ).scalar()
        
        # Estimate 3 minutes per question
        estimated_study_minutes = (weekly_questions or 0) * 3
        
        children_data.append({
            "child_id": child.id,
            "name": child.full_name,
            "class": child.student_class,
            "email": child.email,
            "stats": {
                "total_questions": total_questions or 0,
                "recent_exam_scores": exam_scores,
                "average_score": round(sum(exam_scores) / len(exam_scores), 2) if exam_scores else 0,
                "weekly_study_minutes": estimated_study_minutes
            },
            "subjects": all_subjects,
            "weak_subjects": weak_subjects,
            "last_active": child.last_login.isoformat() if child.last_login else None
        })
    
    return {
        "parent": {
            "name": current_user.full_name,
            "email": current_user.email
        },
        "total_children": len(children),
        "children": children_data
    }


@router.post("/parent/link-child")
async def link_child_to_parent(
    request: LinkChildRequest,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Link a child account to the current parent account
    The child account must already exist and be a student
    """
    # Find the child by email
    child = db.query(User).filter(User.email == request.child_email).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child account not found. Please ensure your child has registered."
        )
    
    # Verify the child is a student
    if child.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The account must be a student account"
        )
    
    # Check if child already has a parent
    if child.parent_id is not None:
        if child.parent_id == current_user.id:
            return {
                "message": "Child is already linked to your account",
                "child_id": child.id,
                "child_name": child.full_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This child account is already linked to another parent"
            )
    
    # Link the child to the parent
    child.parent_id = current_user.id
    db.commit()
    db.refresh(child)
    
    return {
        "message": "Child linked successfully",
        "child_id": child.id,
        "child_name": child.full_name,
        "child_email": child.email
    }


@router.get("/parent/child/{child_id}/detailed")
async def get_child_detailed_report(
    child_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get detailed report for a specific child
    """
    # Verify child belongs to this parent
    child = db.query(User).filter(
        User.id == child_id,
        User.parent_id == current_user.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found or not linked to your account"
        )
    
    # Get comprehensive stats (reuse student dashboard logic)
    # This is similar to student dashboard but from parent's view
    total_questions = db.query(func.count(QuestionHistory.id)).filter(
        QuestionHistory.user_id == child.id
    ).scalar()
    
    # Recent activity
    recent_questions = db.query(QuestionHistory).filter(
        QuestionHistory.user_id == child.id
    ).order_by(QuestionHistory.solved_at.desc()).limit(10).all()
    
    recent_activity = [{
        "date": q.solved_at,
        "subject": q.subject,
        "topic": q.topic
    } for q in recent_questions]
    
    # Exam history
    exams = db.query(ExamAttempt).filter(
        ExamAttempt.user_id == child.id,
        ExamAttempt.completed_at.isnot(None)
    ).order_by(ExamAttempt.completed_at.desc()).all()
    
    exam_history = [{
        "date": exam.completed_at,
        "subject": exam.subject,
        "score": exam.score_percentage,
        "weak_topics": exam.weak_topics
    } for exam in exams]
    
    return {
        "child": {
            "name": child.full_name,
            "class": child.student_class,
            "email": child.email
        },
        "summary": {
            "total_questions": total_questions or 0,
            "total_exams": len(exams),
            "last_active": child.last_login
        },
        "recent_activity": recent_activity,
        "exam_history": exam_history,
        "recommendations": [
            "Encourage daily practice",
            "Focus on weak subjects",
            "Take more mock exams"
        ]
    }


def calculate_study_streak(user_id: int, db: Session) -> int:
    """
    Calculate consecutive days of study activity
    """
    # Get distinct dates with activity
    activity_dates = db.query(
        func.date(QuestionHistory.solved_at)
    ).filter(
        QuestionHistory.user_id == user_id
    ).distinct().order_by(
        func.date(QuestionHistory.solved_at).desc()
    ).all()
    
    if not activity_dates:
        return 0
    
    streak = 0
    current_date = datetime.utcnow().date()
    
    for (activity_date,) in activity_dates:
        if activity_date == current_date or activity_date == current_date - timedelta(days=streak):
            streak += 1
            current_date = activity_date
        else:
            break
    
    return streak


