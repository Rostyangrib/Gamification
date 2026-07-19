import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    GUEST = "GUEST"


class Department(str, enum.Enum):
    IT = "IT"
    FINANCE = "FINANCE"
    HR = "HR"
    PUBLIC = "PUBLIC"


class UserLocation(str, enum.Enum):
    OFFICE = "office"
    REMOTE = "remote"
    VPN = "vpn"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", native_enum=True), nullable=False)
    department: Mapped[Department] = mapped_column(
        Enum(Department, name="department", native_enum=True), nullable=False
    )
    clearance_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[UserLocation] = mapped_column(
        Enum(
            UserLocation,
            name="user_location",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    moodle_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_abac_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "department": self.department.value,
            "clearanceLevel": self.clearance_level,
            "location": self.location.value,
            "isActive": self.is_active,
            "moodleId": self.moodle_id,
        }
