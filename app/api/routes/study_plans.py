"""
Study Plans routes - Generate and manage personalized study plans
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.question import StudyPlan
from app.schemas.question import StudyPlanRequest, StudyPlanResponse
from app.services.ai_service import ai_service

router = APIRouter()


@router.post("/generate", response_model=StudyPlanResponse)
async def generate_study_plan(
    request: StudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a personalized study plan using AI
    """
    # Calculate weeks until exam
    if request.exam_date:
        now = datetime.now(timezone.utc)
        exam_date = request.exam_date
        
        # Handle timezone-aware datetime
        if exam_date.tzinfo is not None:
            exam_date_utc = exam_date.astimezone(timezone.utc)
        else:
            # If naive, assume UTC
            exam_date_utc = exam_date.replace(tzinfo=timezone.utc)
        
        # Calculate difference
        delta = exam_date_utc - now
        weeks_until_exam = max(1, delta.days // 7)
    else:
        weeks_until_exam = 12  # Default to 12 weeks
    
    # Generate plan using AI
    try:
        plan_data = ai_service.generate_study_plan(
            subjects=request.subjects,
            hours_per_day=request.hours_per_day,
            days_per_week=request.days_per_week,
            weeks_until_exam=weeks_until_exam,
            weak_areas=request.weak_areas or []
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
    
    # Save to database
    study_plan = StudyPlan(
        user_id=current_user.id,
        plan_name=f"{request.target_exam} Preparation Plan",
        target_exam=request.target_exam,
        exam_date=request.exam_date,
        hours_per_day=request.hours_per_day,
        days_per_week=request.days_per_week,
        weekly_schedule=plan_data.get("weekly_breakdown", []),
        is_active=True,
        completion_percentage=0
    )
    
    # Deactivate previous plans
    db.query(StudyPlan).filter(
        StudyPlan.user_id == current_user.id,
        StudyPlan.is_active == True
    ).update({"is_active": False})
    
    db.add(study_plan)
    db.commit()
    db.refresh(study_plan)
    
    # Format response
    weekly_schedule = []
    for week_data in plan_data.get("weekly_breakdown", []):
        for daily in week_data.get("daily_schedule", []):
            weekly_schedule.append({
                "day": daily.get("day"),
                "time_slot": "Morning/Afternoon",  # Can be enhanced
                "subject": daily.get("subject"),
                "topic": daily.get("topic"),
                "duration_minutes": daily.get("duration_minutes"),
                "activity_type": daily.get("activities", ["study"])[0]
            })
    
    return {
        "id": study_plan.id,
        "plan_name": study_plan.plan_name,
        "target_exam": study_plan.target_exam,
        "exam_date": study_plan.exam_date,
        "hours_per_day": study_plan.hours_per_day,
        "days_per_week": study_plan.days_per_week,
        "weekly_schedule": weekly_schedule,
        "completion_percentage": study_plan.completion_percentage,
        "is_active": study_plan.is_active,
        "created_at": study_plan.created_at
    }


@router.get("/my-plans", response_model=List[StudyPlanResponse])
async def get_my_study_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all study plans for current user
    """
    plans = db.query(StudyPlan).filter(
        StudyPlan.user_id == current_user.id
    ).order_by(StudyPlan.created_at.desc()).all()
    
    result = []
    for plan in plans:
        weekly_schedule = []
        for week_data in plan.weekly_schedule or []:
            for daily in week_data.get("daily_schedule", []):
                weekly_schedule.append({
                    "day": daily.get("day"),
                    "time_slot": "Morning/Afternoon",
                    "subject": daily.get("subject"),
                    "topic": daily.get("topic"),
                    "duration_minutes": daily.get("duration_minutes", 60),
                    "activity_type": daily.get("activities", ["study"])[0] if daily.get("activities") else "study"
                })
        
        result.append({
            "id": plan.id,
            "plan_name": plan.plan_name,
            "target_exam": plan.target_exam,
            "exam_date": plan.exam_date,
            "hours_per_day": plan.hours_per_day,
            "days_per_week": plan.days_per_week,
            "weekly_schedule": weekly_schedule,
            "completion_percentage": plan.completion_percentage,
            "is_active": plan.is_active,
            "created_at": plan.created_at
        })
    
    return result


@router.get("/active", response_model=StudyPlanResponse)
async def get_active_study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current active study plan
    """
    plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == current_user.id,
        StudyPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active study plan found. Please create one."
        )
    
    weekly_schedule = []
    for week_data in plan.weekly_schedule or []:
        for daily in week_data.get("daily_schedule", []):
            weekly_schedule.append({
                "day": daily.get("day"),
                "time_slot": "Morning/Afternoon",
                "subject": daily.get("subject"),
                "topic": daily.get("topic"),
                "duration_minutes": daily.get("duration_minutes", 60),
                "activity_type": daily.get("activities", ["study"])[0] if daily.get("activities") else "study"
            })
    
    return {
        "id": plan.id,
        "plan_name": plan.plan_name,
        "target_exam": plan.target_exam,
        "exam_date": plan.exam_date,
        "hours_per_day": plan.hours_per_day,
        "days_per_week": plan.days_per_week,
        "weekly_schedule": weekly_schedule,
        "completion_percentage": plan.completion_percentage,
        "is_active": plan.is_active,
        "created_at": plan.created_at
    }


@router.put("/{plan_id}/progress")
async def update_plan_progress(
    plan_id: int,
    completion_percentage: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update study plan progress
    """
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found"
        )
    
    plan.completion_percentage = min(100, max(0, completion_percentage))
    db.commit()
    
    return {
        "message": "Progress updated successfully",
        "completion_percentage": plan.completion_percentage
    }


