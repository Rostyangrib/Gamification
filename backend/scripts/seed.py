"""Seed database with users and ABAC policies."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.policy import Policy, PolicyEffect
from app.models.user import Department, User, UserLocation, UserRole

SEED_PASSWORD = "Test123!"

USERS = [
    {
        "email": "admin@test.com",
        "name": "Администратор",
        "role": UserRole.ADMIN,
        "department": Department.IT,
        "clearance_level": 5,
        "location": UserLocation.OFFICE,
        "is_active": True,
    },
    {
        "email": "finance@test.com",
        "name": "Финансовый менеджер",
        "role": UserRole.MANAGER,
        "department": Department.FINANCE,
        "clearance_level": 4,
        "location": UserLocation.OFFICE,
        "is_active": True,
    },
    {
        "email": "hr@test.com",
        "name": "HR Специалист",
        "role": UserRole.EMPLOYEE,
        "department": Department.HR,
        "clearance_level": 3,
        "location": UserLocation.REMOTE,
        "is_active": True,
    },
    {
        "email": "dev@test.com",
        "name": "Разработчик",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 3,
        "location": UserLocation.VPN,
        "is_active": True,
    },
    {
        "email": "guest@test.com",
        "name": "Гость",
        "role": UserRole.GUEST,
        "department": Department.PUBLIC,
        "clearance_level": 0,
        "location": UserLocation.REMOTE,
        "is_active": True,
    },
    {
        "email": "blocked@test.com",
        "name": "Заблокированный",
        "role": UserRole.EMPLOYEE,
        "department": Department.IT,
        "clearance_level": 2,
        "location": UserLocation.OFFICE,
        "is_active": False,
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


def seed() -> None:
    db = SessionLocal()
    try:
        password_hash = hash_password(SEED_PASSWORD)

        for user_data in USERS:
            existing = db.scalar(select(User).where(User.email == user_data["email"]))
            if existing:
                continue
            user = User(**user_data, password_hash=password_hash)
            db.add(user)

        for policy_data in POLICIES:
            existing = db.scalar(select(Policy).where(Policy.name == policy_data["name"]))
            if existing:
                continue
            db.add(Policy(**policy_data, is_active=True))

        db.commit()
        print("Seed completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
