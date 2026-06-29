from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Department, User, UserLocation, UserRole
from app.schemas.auth import RegisterRequest
from app.services.abac import AbacDecision, AbacEngine


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.abac = AbacEngine(db)

    def register(self, data: RegisterRequest) -> User:
        existing = self.db.scalar(select(User).where(User.email == data.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role=UserRole.EMPLOYEE,
            department=Department.IT,
            clearance_level=1,
            location=UserLocation.REMOTE,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = self.db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.password_hash):
            if user:
                self.abac._write_audit(
                    user.id,
                    "login",
                    AbacDecision(False, "Неверный пароль"),
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

        decision = self.abac.evaluate_access(user, "login")
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "Вход запрещён", "reason": decision.reason},
            )

        token = create_access_token(user.id, user.email)
        return user, token

    def check_access(self, email: str) -> tuple[bool, str]:
        user = self.db.scalar(select(User).where(User.email == email))
        if not user:
            return False, "Пользователь не найден"

        decision = self.abac.evaluate_access(user, "login", write_audit=False)
        return decision.allowed, decision.reason
