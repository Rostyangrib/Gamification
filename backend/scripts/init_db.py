"""Инициализация БД: создание таблиц и seed (аналог init_db из gamification)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import AuditLog, ExternalService, Policy, User  # noqa: F401 — регистрируем модели
from app.models.policy import PolicyEffect
from app.models.user import Department, UserLocation, UserRole

SEED_PASSWORD = "Moodle123!"

USERS = [
    {
        "email": "admin@admin.com",
        "name": "Admin Admin",
        "role": UserRole.ADMIN,
        "department": Department.IT,
        "clearance_level": 5,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": 4,
    },
    {
        "email": "wotblitz1191@gmail.com",
        "name": "u1_name u1_lastname",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 3,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": 5,
    },
    {
        "email": "u2@user.com",
        "name": "u2_name u2_lastname",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 3,
        "location": UserLocation.VPN,
        "is_active": True,
        "moodle_id": 6,
    },
    {
        "email": "sss@ss.s",
        "name": "sss ssss",
        "role": UserRole.ADMIN,
        "department": Department.IT,
        "clearance_level": 5,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": 7,
    },
    {
        "email": "manager@work.com",
        "name": "Анна Иванова",
        "role": UserRole.MANAGER,
        "department": Department.HR,
        "clearance_level": 4,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": 8,
    },
    {
        "email": "dmitry@work.com",
        "name": "Дмитрий Сидоров",
        "role": UserRole.EMPLOYEE,
        "department": Department.FINANCE,
        "clearance_level": 3,
        "location": UserLocation.REMOTE,
        "is_active": True,
        "moodle_id": 9,
    },
    {
        "email": "admin@test.com",
        "name": "Администратор",
        "role": UserRole.ADMIN,
        "department": Department.IT,
        "clearance_level": 5,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": None,
    },
    {
        "email": "finance@test.com",
        "name": "Финансовый менеджер",
        "role": UserRole.MANAGER,
        "department": Department.FINANCE,
        "clearance_level": 4,
        "location": UserLocation.OFFICE,
        "is_active": True,
        "moodle_id": None,
    },
    {
        "email": "hr@test.com",
        "name": "HR Специалист",
        "role": UserRole.EMPLOYEE,
        "department": Department.HR,
        "clearance_level": 3,
        "location": UserLocation.REMOTE,
        "is_active": True,
        "moodle_id": None,
    },
    {
        "email": "dev@test.com",
        "name": "Разработчик",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 3,
        "location": UserLocation.VPN,
        "is_active": True,
        "moodle_id": None,
    },
    {
        "email": "guest@test.com",
        "name": "Гость",
        "role": UserRole.GUEST,
        "department": Department.PUBLIC,
        "clearance_level": 0,
        "location": UserLocation.REMOTE,
        "is_active": True,
        "moodle_id": None,
    },
    {
        "email": "blocked@test.com",
        "name": "Заблокированный",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 2,
        "location": UserLocation.OFFICE,
        "is_active": False,
        "moodle_id": None,
    },
]

POLICIES = [
    {
        "name": "deny-inactive",
        "effect": PolicyEffect.DENY,
        "priority": 100,
        "target": {"action": "login"},
        "condition": {"op": "eq", "left": "$.user.isActive", "right": False},
        "reason": "Аккаунт деактивирован",
    },
    {
        "name": "deny-guest",
        "effect": PolicyEffect.DENY,
        "priority": 90,
        "target": {"action": "login"},
        "condition": {"op": "eq", "left": "$.user.role", "right": "GUEST"},
        "reason": "Гостям вход запрещён",
    },
    {
        "name": "deny-remote-outside-hours",
        "effect": PolicyEffect.DENY,
        "priority": 80,
        "target": {"action": "login"},
        "condition": {
            "op": "and",
            "operands": [
                {"op": "eq", "left": "$.user.location", "right": "remote"},
                {
                    "op": "not",
                    "operand": {
                        "op": "and",
                        "operands": [
                            {"op": "gte", "left": "$.env.currentTime.hour", "right": 9},
                            {"op": "lt", "left": "$.env.currentTime.hour", "right": 18},
                        ],
                    },
                },
            ],
        },
        "reason": "Удалённым сотрудникам вход разрешён только в рабочее время 9:00-18:00",
    },
    {
        "name": "deny-low-clearance-weekend",
        "effect": PolicyEffect.DENY,
        "priority": 70,
        "target": {"action": "login"},
        "condition": {
            "op": "and",
            "operands": [
                {"op": "lt", "left": "$.user.clearanceLevel", "right": 2},
                {"op": "eq", "left": "$.env.currentTime.isWeekend", "right": True},
            ],
        },
        "reason": "Низкий уровень допуска — вход в выходные запрещён",
    },
    {
        "name": "allow-default",
        "effect": PolicyEffect.ALLOW,
        "priority": 1,
        "target": {"action": "login"},
        "condition": {"op": "eq", "left": True, "right": True},
        "reason": "Доступ разрешён",
    },
]


def _seed_users(db, *, force: bool) -> None:
    password_hash = hash_password(SEED_PASSWORD)
    for user_data in USERS:
        existing = db.scalar(select(User).where(User.email == user_data["email"]))
        if existing:
            if user_data.get("moodle_id") is not None and existing.moodle_id != user_data["moodle_id"]:
                existing.moodle_id = user_data["moodle_id"]
            continue
        db.add(User(**user_data, password_hash=password_hash))
    db.commit()
    print("Users seeded.")


def _seed_policies(db, *, force: bool) -> None:
    for policy_data in POLICIES:
        existing = db.scalar(select(Policy).where(Policy.name == policy_data["name"]))
        if existing:
            continue
        db.add(Policy(**policy_data, is_active=True))
    db.commit()
    print("Policies seeded.")


def init_db() -> None:
    print("Creating tables if needed...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS moodle_id INTEGER;"))
        db.commit()

        reset = os.getenv("INIT_DB", "false").lower() == "true"
        if reset:
            print("INIT_DB=true — resetting seed tables...")
            db.execute(text("TRUNCATE TABLE audit_logs, policies, users RESTART IDENTITY CASCADE;"))
            db.commit()

        _seed_users(db, force=reset)
        _seed_policies(db, force=reset)

    print("init_db completed successfully.")


if __name__ == "__main__":
    init_db()
