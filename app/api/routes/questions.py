"""
Questions routes - Solving questions with AI and Vision (GPT-4o-mini)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from PIL import Image
import io
import base64
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserSubject
from app.models.question import QuestionHistory
from app.schemas.question import (
    QuestionSolveRequest,
    QuestionSolveResponse,
    QuestionHistoryResponse,
    SolutionStep
)
from app.services.ai_service import ai_service

router = APIRouter()


def _format_solution_for_db(solution) -> str:
    """
    Convert solution to string format for database storage.
    Handles both string and dict formats from AI responses.
    """
    if isinstance(solution, dict):
        # Convert dict to formatted JSON string for readability
        return json.dumps(solution, indent=2)
    elif isinstance(solution, list):
        # Convert list to JSON string
        return json.dumps(solution, indent=2)
    else:
        # Already a string or can be converted to string
        return str(solution) if solution else ""


def _format_solution_for_response(solution) -> str:
    """
    Convert solution to readable string format for API response.
    Formats dicts as readable text, not JSON.
    """
    if isinstance(solution, dict):
        # Convert dict to readable text format
        lines = []
        for key, value in solution.items():
            # Format key nicely (e.g., "final_velocity" -> "Final Velocity")
            formatted_key = key.replace("_", " ").title()
            lines.append(f"{formatted_key}: {value}")
        return "\n".join(lines)
    elif isinstance(solution, list):
        # Convert list to bullet points
        return "\n".join(f"• {item}" for item in solution)
    else:
        # Already a string or can be converted to string
        return str(solution) if solution else ""


@router.post("/solve", response_model=QuestionSolveResponse)
async def solve_question(
    request: QuestionSolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Solve a question using AI
    - For text questions: Uses standard GPT-4o-mini
    - For images (base64): Uses GPT-4o-mini vision capabilities
    """
    question_text = request.question_text
    solution_data = None
    
    # If image is provided, use vision capabilities
    if request.question_image:
        try:
            # Determine image type from base64 header or default to jpeg
            image_type = "image/jpeg"
            if request.question_image.startswith("data:"):
                # Extract MIME type from data URL
                parts = request.question_image.split(",")
                if len(parts) == 2:
                    image_type = parts[0].split(":")[1].split(";")[0]
                    request.question_image = parts[1]
            
            # Use AI vision to solve the question from the image
            solution_data = ai_service.solve_question_with_image(
                image_base64=request.question_image,
                subject=request.subject,
                additional_context=question_text,  # Use any provided text as additional context
                image_type=image_type
            )
            
            # Get the question text that the AI identified from the image
            question_text = solution_data.get("question_text", question_text or "Question from image")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Vision AI failed: {str(e)}"
            )
    else:
        # Text-only question
        if not question_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide either question text or image"
            )
        
        # Solve question using AI
        try:
            solution_data = ai_service.solve_question(
                question_text=question_text,
                subject=request.subject
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI service error: {str(e)}"
            )
    
    # Save to database
    question_history = QuestionHistory(
        user_id=current_user.id,
        question_text=question_text,
        question_image_url=request.question_image if request.question_image else None,
        subject=solution_data.get("subject"),
        topic=solution_data.get("topic"),
        ai_solution=_format_solution_for_db(solution_data.get("solution", "")),
        steps=solution_data.get("steps"),
        related_topics=solution_data.get("related_topics")
    )
    
    db.add(question_history)
    
    # Update user subject statistics
    subject_name = solution_data.get("subject")
    if subject_name:
        user_subject = db.query(UserSubject).filter(
            UserSubject.user_id == current_user.id,
            UserSubject.subject_name == subject_name
        ).first()
        
        if user_subject:
            user_subject.total_questions_attempted += 1
        else:
            # Create new subject entry
            user_subject = UserSubject(
                user_id=current_user.id,
                subject_name=subject_name,
                total_questions_attempted=1
            )
            db.add(user_subject)
    
    db.commit()
    db.refresh(question_history)
    
    # Format steps for response
    steps = [
        SolutionStep(**step) for step in solution_data.get("steps", [])
    ]
    
    return {
        "question_id": question_history.id,
        "question_text": question_text,
        "subject": solution_data.get("subject", "Unknown"),
        "topic": solution_data.get("topic", "Unknown"),
        "solution": _format_solution_for_response(solution_data.get("solution", "")),
        "steps": steps,
        "related_topics": solution_data.get("related_topics", []),
        "similar_questions": []  # TODO: Implement similar questions feature
    }


@router.post("/solve-with-image", response_model=QuestionSolveResponse)
async def solve_question_with_image(
    image: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    additional_context: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Solve a question from an uploaded image file using GPT-4o-mini Vision
    
    - image: The image file containing the question
    - subject: Optional subject hint (e.g., "Mathematics", "Physics")
    - additional_context: Optional additional text context from the user
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Read and process image
    try:
        image_data = await image.read()
        
        # Validate it's a real image
        pil_image = Image.open(io.BytesIO(image_data))
        pil_image.verify()  # Verify it's a valid image
        
        # Convert image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Get the image type
        image_type = image.content_type or "image/jpeg"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
    
    # Use AI Vision to solve the question
    try:
        solution_data = ai_service.solve_question_with_image(
            image_base64=base64_image,
            subject=subject,
            additional_context=additional_context,
            image_type=image_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision AI service error: {str(e)}"
        )
    
    # Get the question text identified from the image
    question_text = solution_data.get("question_text", "Question from image")
    
    # Save to database
    question_history = QuestionHistory(
        user_id=current_user.id,
        question_text=question_text,
        question_image_url=f"base64:{base64_image[:50]}...",  # Store truncated ref
        subject=solution_data.get("subject"),
        topic=solution_data.get("topic"),
        ai_solution=_format_solution_for_db(solution_data.get("solution", "")),
        steps=solution_data.get("steps"),
        related_topics=solution_data.get("related_topics")
    )
    
    db.add(question_history)
    
    # Update user subject statistics
    subject_name = solution_data.get("subject")
    if subject_name:
        user_subject = db.query(UserSubject).filter(
            UserSubject.user_id == current_user.id,
            UserSubject.subject_name == subject_name
        ).first()
        
        if user_subject:
            user_subject.total_questions_attempted += 1
        else:
            user_subject = UserSubject(
                user_id=current_user.id,
                subject_name=subject_name,
                total_questions_attempted=1
            )
            db.add(user_subject)
    
    db.commit()
    db.refresh(question_history)
    
    # Format steps for response
    steps = [
        SolutionStep(**step) for step in solution_data.get("steps", [])
    ]
    
    return {
        "question_id": question_history.id,
        "question_text": question_text,
        "subject": solution_data.get("subject", "Unknown"),
        "topic": solution_data.get("topic", "Unknown"),
        "solution": _format_solution_for_response(solution_data.get("solution", "")),
        "steps": steps,
        "related_topics": solution_data.get("related_topics", []),
        "similar_questions": []
    }


@router.get("/history", response_model=List[QuestionHistoryResponse])
async def get_question_history(
    limit: int = 50,
    offset: int = 0,
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's question history
    """
    query = db.query(QuestionHistory).filter(
        QuestionHistory.user_id == current_user.id
    )
    
    # Filter by subject if provided
    if subject:
        query = query.filter(QuestionHistory.subject == subject)
    
    # Order by most recent first
    query = query.order_by(QuestionHistory.solved_at.desc())
    
    # Pagination
    questions = query.offset(offset).limit(limit).all()
    
    return questions


@router.get("/history/{question_id}", response_model=QuestionSolveResponse)
async def get_question_detail(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed solution for a specific question from history
    """
    question = db.query(QuestionHistory).filter(
        QuestionHistory.id == question_id,
        QuestionHistory.user_id == current_user.id
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    steps = [SolutionStep(**step) for step in (question.steps or [])]
    
    return {
        "question_id": question.id,
        "question_text": question.question_text,
        "subject": question.subject or "Unknown",
        "topic": question.topic or "Unknown",
        "solution": question.ai_solution,
        "steps": steps,
        "related_topics": question.related_topics or [],
        "similar_questions": []
    }
