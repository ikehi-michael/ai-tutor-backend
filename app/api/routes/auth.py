"""
Authentication routes - Registration, Login, Profile
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token,
    get_current_user
)
from app.models.user import User, UserSubject, UserRole
from app.schemas.user import (
    UserRegister, 
    UserLogin, 
    Token, 
    UserProfile,
    UserUpdate
)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user (student, parent, or admin)
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone already exists (if provided)
    if user_data.phone:
        existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        student_class=user_data.student_class,
        is_active=True,
        subscription_tier="free"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Add subjects if provided
    if user_data.subjects:
        for subject_name in user_data.subjects:
            user_subject = UserSubject(
                user_id=new_user.id,
                subject_name=subject_name
            )
            db.add(user_subject)
        db.commit()
    
    # Create access token - use string for sub claim
    access_token = create_access_token(
        data={"sub": str(new_user.id), "role": str(new_user.role.value) if hasattr(new_user.role, 'value') else str(new_user.role)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "role": new_user.role
    }


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email/username and password (OAuth2 compatible)
    Use your email as username in Swagger authorize
    """
    # Find user by email (username field contains email)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token - use string for sub claim
    access_token = create_access_token(
        data={"sub": str(user.id), "role": str(user.role.value) if hasattr(user.role, 'value') else str(user.role)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role
    }


@router.post("/login/json", response_model=Token)
async def login_user_json(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with JSON body (for frontend app)
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token - use string for sub claim
    access_token = create_access_token(
        data={"sub": str(user.id), "role": str(user.role.value) if hasattr(user.role, 'value') else str(user.role)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role
    }


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile
    """
    # Load subjects with accuracy calculation
    subjects_data = []
    for subject in current_user.subjects:
        accuracy = None
        if subject.total_questions_attempted > 0:
            accuracy = (subject.correct_answers / subject.total_questions_attempted) * 100
        
        subjects_data.append({
            "id": subject.id,
            "subject_name": subject.subject_name,
            "total_questions_attempted": subject.total_questions_attempted,
            "correct_answers": subject.correct_answers,
            "accuracy": round(accuracy, 2) if accuracy else None
        })
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "student_class": current_user.student_class,
        "subscription_tier": current_user.subscription_tier,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
        "subjects": subjects_data
    }


@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    """
    # Update fields if provided
    if update_data.full_name:
        current_user.full_name = update_data.full_name
    
    if update_data.phone:
        # Check if phone is already used by another user
        existing_phone = db.query(User).filter(
            User.phone == update_data.phone,
            User.id != current_user.id
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use"
            )
        current_user.phone = update_data.phone
    
    if update_data.student_class:
        current_user.student_class = update_data.student_class
    
    # Update subjects if provided
    if update_data.subjects is not None:
        # Remove old subjects
        db.query(UserSubject).filter(UserSubject.user_id == current_user.id).delete()
        
        # Add new subjects
        for subject_name in update_data.subjects:
            user_subject = UserSubject(
                user_id=current_user.id,
                subject_name=subject_name
            )
            db.add(user_subject)
    
    db.commit()
    db.refresh(current_user)
    
    # Return updated profile
    return await get_my_profile(current_user, db)


