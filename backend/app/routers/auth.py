from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthCheckResponse,
    CheckAccessRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> User:
    return AuthService(db).register(data)


@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user, token = AuthService(db).authenticate(data.email, data.password)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        secure=False,
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(key=settings.cookie_name)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/check", response_model=AuthCheckResponse)
def check_access(data: CheckAccessRequest, db: Session = Depends(get_db)) -> AuthCheckResponse:
    allowed, reason = AuthService(db).check_access(data.email)
    return AuthCheckResponse(allowed=allowed, reason=reason)
