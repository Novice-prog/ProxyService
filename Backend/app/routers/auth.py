from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.tasks.email import send_activation_key
from app.tasks.activation_keys import issue_activation_key
from app.db.deps import get_db
from app.db.models import Admin, User
from app.schemas.auth import AccessTokenResponse, MessageResponse, RefreshTokenRequest, TokenResponse, UserLoginRequest, UserRegisterRequest
from app.core.security import (
    create_access_token,
    create_admin_access_token,
    create_admin_refresh_token,
    create_refresh_token,
    generate_activation_key,
    get_token_subject,
    hash_password,
    verify_password,
)
from datetime import datetime, UTC, timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(
        data: UserRegisterRequest,
        db: Session = Depends(get_db),
    ):

    if data.password != data.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "Password do not match",
        )
    
    existing_user = db.scalar(select(User).where(User.email == data.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "User with this email already exists"
        )
    
    user = User(
        email = data.email,
        password_hash = hash_password(data.password),
        is_active = True,
    )

    activation_key = issue_activation_key(
        db = db,
        user = user,
    )


    db.add(user)
    db.commit()

    send_activation_key.delay(
        email = user.email, 
        activation_key = activation_key,
    )

    return {
        "message" : "User registered successfully. Activation key email queued."
    }


@router.post("/login", response_model=TokenResponse)
def login(
        data: UserLoginRequest,
        db: Session = Depends(get_db)
    ):

    user = db.scalar(
        select(User).where(User.email == data.email)
    )
    
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return {
        "access_token" : create_access_token(user.id),
        "refresh_token" : create_refresh_token(user.id),
        "token_type" : "bearer"
    }

@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(data: RefreshTokenRequest):
    subject = get_token_subject(
        data.refresh_token,
        expected_type="refresh"
    )

    if subject is None: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid refresh token"
        )
    
    return{
        "access_token": create_access_token(subject),
        "token_type": "bearer"
    }

@router.post("/token", response_model = TokenResponse)
def swagger_login(
    data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.scalar(
        select(User).where(User.email == data.username)
    )

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(
    data: UserLoginRequest,
    db: Session = Depends(get_db),
):
    admin = db.scalar(select(Admin).where(Admin.email == data.email))

    if admin is None or not verify_password(data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return {
        "access_token": create_admin_access_token(admin.id),
        "refresh_token": create_admin_refresh_token(admin.id),
        "token_type": "bearer",
    }

