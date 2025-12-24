"""
Topics routes - Topic teaching and explanations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import re
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.question import SavedLesson, LessonChat
from app.schemas.question import (
    TopicTeachRequest, 
    TopicTeachResponse,
    SavedLessonResponse,
    LessonChatRequest,
    LessonChatResponse,
    LessonChatMessage
)
from app.services.ai_service import ai_service
from app.services.youtube_service import youtube_service

router = APIRouter()


# Nigerian WAEC/JAMB subject list
AVAILABLE_SUBJECTS = [
    "Mathematics",
    "English Language",
    "Physics",
    "Chemistry",
    "Biology",
    "Economics",
    "Geography",
    "Government",
    "Literature in English",
    "Commerce",
    "Accounting",
    "Agricultural Science",
    "Civic Education",
    "Computer Studies",
    "Further Mathematics"
]


@router.get("/subjects")
async def get_available_subjects():
    """
    Get list of available subjects
    """
    return {
        "subjects": AVAILABLE_SUBJECTS,
        "total": len(AVAILABLE_SUBJECTS)
    }


def extract_youtube_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    if not url:
        return None
    
    # Pattern for various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


@router.post("/teach", response_model=TopicTeachResponse)
async def teach_topic(
    request: TopicTeachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI teaching explanation for a specific topic
    Automatically saves the lesson for future access
    """
    # Validate subject
    if request.subject not in AVAILABLE_SUBJECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject not available. Choose from: {', '.join(AVAILABLE_SUBJECTS)}"
        )
    
    difficulty = request.difficulty_level or "medium"
    
    # Check if lesson already exists
    existing_lesson = db.query(SavedLesson).filter(
        and_(
            SavedLesson.user_id == current_user.id,
            SavedLesson.subject == request.subject,
            SavedLesson.topic == request.topic,
            SavedLesson.difficulty_level == difficulty
        )
    ).first()
    
    if existing_lesson:
        # Update last accessed time
        existing_lesson.last_accessed_at = datetime.now()
        db.commit()
        
        # Return saved lesson
        lesson_data = existing_lesson.lesson_data
        return {
            "subject": existing_lesson.subject,
            "topic": existing_lesson.topic,
            "summary": lesson_data.get("summary", ""),
            "detailed_explanation": lesson_data.get("detailed_explanation", ""),
            "examples": lesson_data.get("examples", []),
            "practice_questions": lesson_data.get("practice_questions", []),
            "video_link": existing_lesson.youtube_video_url,
            "youtube_video_id": existing_lesson.youtube_video_id,
            "lesson_id": existing_lesson.id
        }
    
    # Get teaching content from AI
    try:
        teaching_data = ai_service.teach_topic(
            subject=request.subject,
            topic=request.topic,
            difficulty=difficulty
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
    
    # Format examples
    examples = []
    for example in teaching_data.get("examples", []):
        if isinstance(example, dict):
            examples.append(f"Problem: {example.get('problem', '')}\nSolution: {example.get('solution', '')}")
        else:
            examples.append(str(example))
    
    # Search for YouTube video using YouTube Data API v3
    youtube_video_info = None
    try:
        youtube_video_info = youtube_service.search_educational_video(
            subject=request.subject,
            topic=request.topic
        )
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        # Continue without YouTube video if search fails
    
    youtube_video_id = None
    youtube_url = None
    if youtube_video_info:
        youtube_video_id = youtube_video_info.get("video_id")
        youtube_url = youtube_video_info.get("video_url")
    
    # Prepare lesson data for saving
    lesson_data = {
        "summary": teaching_data.get("summary", ""),
        "detailed_explanation": teaching_data.get("detailed_explanation", ""),
        "examples": examples,
        "practice_questions": teaching_data.get("practice_questions", []),
        "key_concepts": teaching_data.get("key_concepts", []),
        "common_mistakes": teaching_data.get("common_mistakes", []),
        "exam_tips": teaching_data.get("exam_tips", [])
    }
    
    # Save lesson to database
    saved_lesson = SavedLesson(
        user_id=current_user.id,
        subject=request.subject,
        topic=request.topic,
        difficulty_level=difficulty,
        lesson_data=lesson_data,
        youtube_video_id=youtube_video_id,
        youtube_video_url=youtube_url if youtube_url and youtube_url != "null" else None
    )
    db.add(saved_lesson)
    db.commit()
    db.refresh(saved_lesson)
    
    return {
        "subject": request.subject,
        "topic": request.topic,
        "summary": lesson_data["summary"],
        "detailed_explanation": lesson_data["detailed_explanation"],
        "examples": lesson_data["examples"],
        "practice_questions": lesson_data["practice_questions"],
        "video_link": youtube_url if youtube_url and youtube_url != "null" else None,
        "youtube_video_id": youtube_video_id,
        "lesson_id": saved_lesson.id
    }


@router.post("/simplify")
async def simplify_explanation(
    topic: str,
    original_explanation: str,
    current_user: User = Depends(get_current_user)
):
    """
    Simplify an explanation (for "Explain Again in Simpler Way" button)
    """
    try:
        simplified = ai_service.simplify_explanation(
            original_explanation=original_explanation,
            topic=topic
        )
        
        return {
            "topic": topic,
            "simplified_explanation": simplified
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )


@router.get("/syllabus/{subject}")
async def get_subject_syllabus(subject: str):
    """
    Get syllabus topics for a subject (WAEC/JAMB aligned)
    
    Note: In production, this should come from a database
    For now, returning sample data
    """
    if subject not in AVAILABLE_SUBJECTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    # Sample syllabus data - should be replaced with actual database
    sample_syllabi = {
        "Mathematics": [
            "Number and Numeration",
            "Algebraic Processes",
            "Quadratic Equations",
            "Linear and Quadratic Graphs",
            "Trigonometry",
            "Geometry and Mensuration",
            "Statistics and Probability",
            "Calculus (Differentiation and Integration)"
        ],
        "Physics": [
            "Motion",
            "Force and Motion",
            "Energy and Power",
            "Electricity",
            "Magnetism",
            "Waves",
            "Light and Optics",
            "Modern Physics"
        ],
        "Chemistry": [
            "Atomic Structure",
            "Chemical Bonding",
            "Acids, Bases and Salts",
            "Oxidation and Reduction",
            "Organic Chemistry",
            "Periodic Table",
            "Chemical Reactions",
            "Stoichiometry"
        ]
    }
    
    topics = sample_syllabi.get(subject, [])
    
    if not topics:
        # Return empty list for subjects not yet populated
        return {
            "subject": subject,
            "topics": [],
            "message": "Syllabus topics coming soon"
        }
    
    return {
        "subject": subject,
        "topics": topics,
        "total_topics": len(topics)
    }


@router.get("/saved-lessons", response_model=List[SavedLessonResponse])
async def get_saved_lessons(
    subject: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all saved lessons for the current user
    Optionally filter by subject
    """
    query = db.query(SavedLesson).filter(SavedLesson.user_id == current_user.id)
    
    if subject:
        query = query.filter(SavedLesson.subject == subject)
    
    lessons = query.order_by(SavedLesson.last_accessed_at.desc()).all()
    return lessons


@router.get("/saved-lessons/{lesson_id}", response_model=SavedLessonResponse)
async def get_saved_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific saved lesson
    """
    lesson = db.query(SavedLesson).filter(
        and_(
            SavedLesson.id == lesson_id,
            SavedLesson.user_id == current_user.id
        )
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Update last accessed time
    lesson.last_accessed_at = datetime.now()
    db.commit()
    
    return lesson


@router.post("/chat", response_model=LessonChatResponse)
async def chat_about_topic(
    request: LessonChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with AI about a specific topic/lesson
    """
    # Get the lesson
    lesson = db.query(SavedLesson).filter(
        and_(
            SavedLesson.id == request.lesson_id,
            SavedLesson.user_id == current_user.id
        )
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Get chat history for this lesson
    chat_history = db.query(LessonChat).filter(
        LessonChat.lesson_id == request.lesson_id
    ).order_by(LessonChat.created_at.asc()).all()
    
    # Format conversation history
    conversation_history = [
        {"role": msg.role, "message": msg.message}
        for msg in chat_history
    ]
    
    # Get AI response
    try:
        ai_response = ai_service.chat_about_topic(
            subject=lesson.subject,
            topic=lesson.topic,
            user_message=request.message,
            conversation_history=conversation_history
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
    
    # Save user message
    user_msg = LessonChat(
        lesson_id=request.lesson_id,
        user_id=current_user.id,
        role="user",
        message=request.message
    )
    db.add(user_msg)
    
    # Save AI response
    ai_msg = LessonChat(
        lesson_id=request.lesson_id,
        user_id=current_user.id,
        role="assistant",
        message=ai_response
    )
    db.add(ai_msg)
    db.commit()
    
    return {
        "message": ai_response
    }


@router.get("/chat/{lesson_id}/history", response_model=List[LessonChatMessage])
async def get_chat_history(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get chat history for a specific lesson
    """
    # Verify lesson belongs to user
    lesson = db.query(SavedLesson).filter(
        and_(
            SavedLesson.id == lesson_id,
            SavedLesson.user_id == current_user.id
        )
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Get chat messages
    messages = db.query(LessonChat).filter(
        LessonChat.lesson_id == lesson_id
    ).order_by(LessonChat.created_at.asc()).all()
    
    return messages


