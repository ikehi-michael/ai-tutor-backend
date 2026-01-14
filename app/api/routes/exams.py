"""
Mock Exams routes - Generate and manage mock exams
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserSubject
from app.models.question import ExamAttempt, PastQuestion
from app.schemas.question import (
    MockExamRequest,
    MockExamResponse,
    ExamSubmissionRequest,
    ExamResultResponse,
    ExamQuestion
)

router = APIRouter()


# Sample question bank (In production, this should be a database)
SAMPLE_QUESTIONS = {
    "Mathematics": [
        {
            "question": "Simplify: 3x + 5x - 2x",
            "options": {"A": "6x", "B": "8x", "C": "10x", "D": "5x"},
            "correct_answer": "A",
            "topic": "Algebraic Processes"
        },
        {
            "question": "What is the square root of 144?",
            "options": {"A": "10", "B": "11", "C": "12", "D": "13"},
            "correct_answer": "C",
            "topic": "Number and Numeration"
        },
        {
            "question": "Solve for x: 2x + 5 = 15",
            "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
            "correct_answer": "C",
            "topic": "Linear Equations"
        }
    ],
    "English Language": [
        {
            "question": "Choose the correct spelling:",
            "options": {"A": "Recieve", "B": "Receive", "C": "Receeve", "D": "Recive"},
            "correct_answer": "B",
            "topic": "Spelling"
        }
    ]
}


@router.post("/create", response_model=MockExamResponse)
async def create_mock_exam(
    request: MockExamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new mock exam from past questions database
    Falls back to sample questions if no past questions available
    """
    import random
    
    # First, try to get questions from past questions database
    query = db.query(PastQuestion).filter(
        PastQuestion.exam_type == request.exam_type,
        PastQuestion.subject == request.subject,
        PastQuestion.correct_answer.isnot(None)  # Only questions with answers
    )
    
    if request.year and request.year != "Random Mix":
        query = query.filter(PastQuestion.year == request.year)
    
    questions_pool_db = query.all()
    
    # If we have past questions, use them
    if questions_pool_db:
        num_questions = request.number_of_questions or 50
        selected_past_questions = random.sample(
            questions_pool_db,
            min(num_questions, len(questions_pool_db))
        )
        
        # Format questions (hide correct answers)
        exam_questions = []
        questions_for_storage = []
        
        for i, pq in enumerate(selected_past_questions, 1):
            exam_questions.append({
                "question_number": i,
                "question_text": pq.question_text,
                "options": pq.options,
                "correct_answer": None  # Hidden from student
            })
            
            questions_for_storage.append({
                "question": pq.question_text,
                "options": pq.options,
                "correct_answer": pq.correct_answer,
                "topic": pq.topic or "Unknown"
            })
        
        # Create exam attempt record
        exam_attempt = ExamAttempt(
            user_id=current_user.id,
            exam_type=request.exam_type,
            subject=request.subject,
            year=request.year,
            questions=questions_for_storage,
            user_answers={},
            correct_answers={str(i+1): pq.correct_answer for i, pq in enumerate(selected_past_questions)},
            time_limit_minutes=request.time_limit_minutes or 90,
            time_taken_seconds=0,
            total_questions=len(exam_questions),
            correct_count=0,
            score_percentage=0
        )
        
        db.add(exam_attempt)
        db.commit()
        db.refresh(exam_attempt)
        
        return {
            "exam_id": exam_attempt.id,
            "exam_type": request.exam_type,
            "subject": request.subject,
            "total_questions": len(exam_questions),
            "time_limit_minutes": request.time_limit_minutes or 90,
            "questions": [ExamQuestion(**q) for q in exam_questions],
            "started_at": exam_attempt.started_at
        }
    
    # Fallback to sample questions if no past questions available
    questions_pool = SAMPLE_QUESTIONS.get(request.subject, [])
    
    if not questions_pool:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No questions available for {request.subject} {request.exam_type}. Please upload past questions first or try a different subject."
        )
    
    # Select random questions from sample
    selected_questions = random.sample(
        questions_pool,
        min(request.number_of_questions, len(questions_pool))
    )
    
    # Format questions (hide correct answers)
    exam_questions = []
    for i, q in enumerate(selected_questions, 1):
        exam_questions.append({
            "question_number": i,
            "question_text": q["question"],
            "options": q["options"],
            "correct_answer": None  # Hidden from student
        })
    
    # Create exam attempt record
    exam_attempt = ExamAttempt(
        user_id=current_user.id,
        exam_type=request.exam_type,
        subject=request.subject,
        year=request.year,
        questions=selected_questions,  # Store full questions with answers
        user_answers={},  # Will be filled on submission
        correct_answers={str(i+1): q["correct_answer"] for i, q in enumerate(selected_questions)},
        time_limit_minutes=request.time_limit_minutes,
        time_taken_seconds=0,
        total_questions=len(selected_questions),
        correct_count=0,
        score_percentage=0
    )
    
    db.add(exam_attempt)
    db.commit()
    db.refresh(exam_attempt)
    
    return {
        "exam_id": exam_attempt.id,
        "exam_type": request.exam_type,
        "subject": request.subject,
        "total_questions": len(exam_questions),
        "time_limit_minutes": request.time_limit_minutes,
        "questions": [ExamQuestion(**q) for q in exam_questions],
        "started_at": exam_attempt.started_at
    }


@router.post("/submit", response_model=ExamResultResponse)
async def submit_exam(
    submission: ExamSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit exam answers and get results
    """
    # Find exam attempt
    exam = db.query(ExamAttempt).filter(
        ExamAttempt.id == submission.exam_id,
        ExamAttempt.user_id == current_user.id
    ).first()
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found"
        )
    
    if exam.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam already submitted"
        )
    
    # Grade the exam
    correct_count = 0
    detailed_results = []
    weak_topics = {}
    
    for q_num, user_answer in submission.answers.items():
        correct_answer = exam.correct_answers.get(str(q_num))
        is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_count += 1
        else:
            # Track weak topics
            question = exam.questions[int(q_num) - 1]
            topic = question.get("topic", "Unknown")
            weak_topics[topic] = weak_topics.get(topic, 0) + 1
        
        detailed_results.append({
            "question_number": int(q_num),
            "question_text": exam.questions[int(q_num) - 1]["question"],
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "topic": exam.questions[int(q_num) - 1].get("topic", "Unknown")
        })
    
    # Calculate score
    score_percentage = int((correct_count / exam.total_questions) * 100)
    
    # Identify weak topics (topics with most wrong answers)
    weak_topics_list = sorted(weak_topics.items(), key=lambda x: x[1], reverse=True)
    weak_topics_names = [topic for topic, _ in weak_topics_list[:3]]
    
    # Update exam record
    exam.user_answers = submission.answers
    exam.time_taken_seconds = submission.time_taken_seconds
    exam.correct_count = correct_count
    exam.score_percentage = score_percentage
    exam.weak_topics = weak_topics_names
    exam.completed_at = datetime.utcnow()
    
    # Update user subject statistics
    user_subject = db.query(UserSubject).filter(
        UserSubject.user_id == current_user.id,
        UserSubject.subject_name == exam.subject
    ).first()
    
    if user_subject:
        user_subject.total_questions_attempted += exam.total_questions
        user_subject.correct_answers += correct_count
    
    db.commit()
    
    # Generate recommendations
    recommendations = []
    if score_percentage < 50:
        recommendations.append(f"Focus on improving your understanding of {exam.subject} fundamentals")
    if weak_topics_names:
        recommendations.append(f"Spend more time studying: {', '.join(weak_topics_names)}")
    if score_percentage >= 70:
        recommendations.append("Great job! Keep practicing to maintain this level")
    
    return {
        "exam_id": exam.id,
        "total_questions": exam.total_questions,
        "correct_count": correct_count,
        "score_percentage": score_percentage,
        "time_taken_seconds": submission.time_taken_seconds,
        "weak_topics": weak_topics_names,
        "detailed_results": detailed_results,
        "recommendations": recommendations
    }


@router.get("/history", response_model=List[ExamResultResponse])
async def get_exam_history(
    subject: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's exam attempt history
    """
    query = db.query(ExamAttempt).filter(
        ExamAttempt.user_id == current_user.id,
        ExamAttempt.completed_at.isnot(None)
    )
    
    if subject:
        query = query.filter(ExamAttempt.subject == subject)
    
    exams = query.order_by(ExamAttempt.completed_at.desc()).all()
    
    results = []
    for exam in exams:
        results.append({
            "exam_id": exam.id,
            "total_questions": exam.total_questions,
            "correct_count": exam.correct_count,
            "score_percentage": exam.score_percentage,
            "time_taken_seconds": exam.time_taken_seconds,
            "weak_topics": exam.weak_topics or [],
            "detailed_results": [],  # Don't include detailed results in list view
            "recommendations": []
        })
    
    return results


