import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.abac import AbacEngine


def test_condition_operators():
    db = MagicMock()
    engine = AbacEngine(db)
    ctx = {
        "user": {
            "role": "GUEST",
            "isActive": True,
            "clearanceLevel": 1,
            "location": "remote",
        },
        "env": {"currentTime": {"hour": 20, "isWeekend": False}},
    }

    assert engine._evaluate_condition({"op": "eq", "left": "$.user.role", "right": "GUEST"}, ctx)
    assert engine._evaluate_condition({"op": "neq", "left": "$.user.role", "right": "ADMIN"}, ctx)
    assert engine._evaluate_condition({"op": "lt", "left": "$.user.clearanceLevel", "right": 2}, ctx)
    assert engine._evaluate_condition(
        {
            "op": "and",
            "operands": [
                {"op": "eq", "left": "$.user.location", "right": "remote"},
                {"op": "gte", "left": "$.env.currentTime.hour", "right": 18},
            ],
        },
        ctx,
    )
    assert engine._evaluate_condition(
        {"op": "not", "operand": {"op": "eq", "left": "$.user.isActive", "right": True}},
        ctx,
    ) is False


if __name__ == "__main__":
    test_condition_operators()
    print("ABAC unit tests passed")
