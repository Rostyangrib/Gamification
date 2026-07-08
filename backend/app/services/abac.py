from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.policy import Policy, PolicyEffect
from app.models.user import User


class AbacDecision:
    def __init__(self, allowed: bool, reason: str, policy_name: str | None = None):
        self.allowed = allowed
        self.reason = reason
        self.policy_name = policy_name


class AbacEngine:
    def __init__(self, db: Session):
        self.db = db

    def build_environment(self, tz_name: str = "Europe/Moscow") -> dict[str, Any]:
        now = datetime.now(ZoneInfo(tz_name))
        return {
            "currentTime": {
                "hour": now.hour,
                "minute": now.minute,
                "dayOfWeek": now.weekday(),
                "isWeekend": now.weekday() >= 5,
                "iso": now.isoformat(),
            },
            "timezone": tz_name,
        }

    def evaluate_access(
        self,
        user: User,
        action: str,
        environment: dict[str, Any] | None = None,
        *,
        write_audit: bool = True,
    ) -> AbacDecision:
        env = environment or self.build_environment()
        context = {"user": user.to_abac_dict(), "env": env, "action": action}

        policies = self.db.scalars(
            select(Policy)
            .where(Policy.is_active.is_(True))
            .order_by(Policy.priority.desc())
        ).all()

        matching = [p for p in policies if self._target_matches(p.target, action)]
        decision = AbacDecision(False, "Доступ запрещён: не найдено подходящей политики")

        for policy in matching:
            if self._evaluate_condition(policy.condition, context):
                allowed = policy.effect == PolicyEffect.ALLOW
                reason = policy.reason or (
                    "Доступ разрешён" if allowed else "Доступ запрещён политикой"
                )
                decision = AbacDecision(allowed, reason, policy.name)
                break

        if write_audit:
            self._write_audit(user.id, action, decision)

        return decision

    def _target_matches(self, target: dict, action: str) -> bool:
        target_action = target.get("action")
        if target_action is None:
            return True
        if isinstance(target_action, list):
            return action in target_action
        return target_action == action

    def _resolve_path(self, path: str, context: dict) -> Any:
        if not path.startswith("$."):
            return path
        parts = path[2:].split(".")
        current: Any = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        op = condition.get("op")
        if op is None:
            return True

        if op == "and":
            return all(self._evaluate_condition(c, context) for c in condition.get("operands", []))
        if op == "or":
            return any(self._evaluate_condition(c, context) for c in condition.get("operands", []))
        if op == "not":
            return not self._evaluate_condition(condition["operand"], context)

        left = condition.get("left")
        right = condition.get("right")
        left_val = self._resolve_path(left, context) if isinstance(left, str) and left.startswith("$.") else left
        right_val = (
            self._resolve_path(right, context) if isinstance(right, str) and right.startswith("$.") else right
        )

        if op == "eq":
            return left_val == right_val
        if op == "neq":
            return left_val != right_val
        if op == "gt":
            return left_val is not None and right_val is not None and left_val > right_val
        if op == "gte":
            return left_val is not None and right_val is not None and left_val >= right_val
        if op == "lt":
            return left_val is not None and right_val is not None and left_val < right_val
        if op == "lte":
            return left_val is not None and right_val is not None and left_val <= right_val
        if op == "in":
            return left_val in (right_val or [])
        if op == "between":
            low, high = right_val
            return left_val is not None and low <= left_val <= high

        return False

    def _write_audit(self, user_id: int, action: str, decision: AbacDecision) -> None:
        log = AuditLog(
            user_id=user_id,
            action=action,
            result="ALLOW" if decision.allowed else "DENY",
            reason=decision.reason,
        )
        self.db.add(log)
        self.db.commit()
