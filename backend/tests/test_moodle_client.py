import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import moodle_client


def test_find_user_ids_by_email_uses_single_batch_request():
    moodle_users = [
        {"id": 42, "email": "first@example.com"},
        {"id": "81", "email": "SECOND@example.com"},
    ]

    with patch.object(moodle_client, "call", return_value=moodle_users) as call:
        result = moodle_client.find_user_ids_by_email(
            "https://moodle.example.com",
            "token",
            ["First@example.com", " second@example.com ", "FIRST@example.com"],
        )

    assert result == {"first@example.com": 42, "second@example.com": 81}
    call.assert_called_once_with(
        "https://moodle.example.com",
        "token",
        "core_user_get_users_by_field",
        field="email",
        values=["first@example.com", "second@example.com"],
    )
