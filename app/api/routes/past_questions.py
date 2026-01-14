"""
Past Questions routes - Upload and manage past exam questions
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.question import PastQuestion
from app.services.pq_processor import pq_processor
from app.schemas.question import (
    PastQuestionResponse, 
    AvailablePastQuestionsResponse
)
import os
import tempfile

router = APIRouter()


@router.post("/upload", response_model=List[PastQuestionResponse])
async def upload_past_questions(
    file: UploadFile = File(...),
    exam_type: str = Form(...),
    subject: str = Form(...),
    year: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF file containing past questions and extract questions
    
    Note: In production, restrict this to admin users only
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Process PDF
        questions_data = pq_processor.process_pdf(tmp_path, exam_type, subject, year)
        
        if not questions_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No questions could be extracted from the PDF. Please check the file format."
            )
        
        # Filter out questions without correct answers (they can't be used in exams)
        valid_questions = [q for q in questions_data if q.get("correct_answer")]
        questions_without_answers = len(questions_data) - len(valid_questions)
        
        if not valid_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No questions with correct answers could be extracted from the PDF. Please ensure answers are marked in the PDF."
            )
        
        # Save to database
        saved_questions = []
        for q_data in valid_questions:
            # Ensure correct_answer is not None
            if not q_data.get("correct_answer"):
                continue
                
            # Check if question already exists
            existing = db.query(PastQuestion).filter(
                PastQuestion.exam_type == exam_type,
                PastQuestion.subject == subject,
                PastQuestion.year == year,
                PastQuestion.question_number == q_data["question_number"]
            ).first()
            
            if existing:
                # Update existing
                existing.question_text = q_data["question_text"]
                existing.options = q_data["options"]
                existing.correct_answer = q_data.get("correct_answer")
                existing.topic = q_data.get("topic")
                existing.page_number = q_data.get("page_number")
                existing.source_pdf = q_data.get("source_pdf", file.filename)
                saved_questions.append(existing)
            else:
                # Create new
                pq = PastQuestion(
                    exam_type=exam_type,
                    subject=subject,
                    year=year,
                    question_number=q_data["question_number"],
                    question_text=q_data["question_text"],
                    options=q_data["options"],
                    correct_answer=q_data.get("correct_answer"),
                    topic=q_data.get("topic"),
                    source_pdf=q_data.get("source_pdf", file.filename),
                    page_number=q_data.get("page_number")
                )
                db.add(pq)
                saved_questions.append(pq)
        
        db.commit()
        
        # Refresh all saved questions
        for pq in saved_questions:
            db.refresh(pq)
        
        # Log warning if some questions were skipped
        if questions_without_answers > 0:
            print(f"Warning: {questions_without_answers} questions were skipped because they don't have correct answers.")
        
        return saved_questions
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


@router.get("/available", response_model=List[AvailablePastQuestionsResponse])
async def get_available_past_questions(
    exam_type: str = None,
    subject: str = None,
    year: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of available past questions grouped by exam_type, subject, year
    """
    from sqlalchemy import distinct, func
    
    query = db.query(
        PastQuestion.exam_type,
        PastQuestion.subject,
        PastQuestion.year
    ).distinct()
    
    if exam_type:
        query = query.filter(PastQuestion.exam_type == exam_type)
    if subject:
        query = query.filter(PastQuestion.subject == subject)
    if year:
        query = query.filter(PastQuestion.year == year)
    
    results = query.all()
    
    available = []
    for r in results:
        count = db.query(PastQuestion).filter(
            PastQuestion.exam_type == r[0],
            PastQuestion.subject == r[1],
            PastQuestion.year == r[2]
        ).count()
        
        available.append({
            "exam_type": r[0],
            "subject": r[1],
            "year": r[2],
            "question_count": count
        })
    
    return available
