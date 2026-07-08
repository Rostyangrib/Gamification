"""Упрощение JSON-ответов Moodle API (эндпоинты из server.py)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Callable

if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

COMPLETION_STATE = {
    0: "incomplete",
    1: "complete",
    2: "complete_pass",
    3: "complete_fail",
}

TRACKING = {0: "none", 1: "manual", 2: "automatic"}

MOODLE_SOURCES = (
    "core_completion_get_activities_completion_status",
    "core_completion_get_course_completion_status",
    "core_course_get_courses",
    "core_course_completion_status",
    "core_enrol_get_enrolled_users",
    "core_enrol_get_users_courses",
    "core_user_get_users",
    "get_course_progress",
    "gradereport_user_get_grade_items",
    "gradereport_user_get_grades_table",
)

_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    return _HTML_TAG.sub("", value).strip()


def _pick(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: data[key] for key in keys if key in data}


def _as_bool(value: Any) -> bool | Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    return value


def _format_date(value: Any) -> str | None:
    if value is None or value == 0:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    return None


def _format_datetime(value: Any) -> str | None:
    if value is None or value == 0:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")
    return None


def _normalize_source(name: str) -> str:
    for source in MOODLE_SOURCES:
        if name == source or name.startswith(f"{source}_"):
            return source
    return name


def simplify_activities_completion(data: dict[str, Any]) -> dict[str, Any]:
    activities = []
    for item in data.get("statuses", []):
        state = item.get("state")
        activities.append(
            {
                "cmid": item.get("cmid"),
                "module": item.get("modname"),
                "state": COMPLETION_STATE.get(state, state),
                "completed_at": _format_datetime(item.get("timecompleted")),
            }
        )
    return {"activities": activities}


def simplify_course_completion(data: dict[str, Any]) -> dict[str, Any]:
    status = data.get("completionstatus", {})
    criteria = []
    for item in status.get("completions", []):
        criteria.append(
            {
                "title": item.get("title"),
                "status": item.get("status"),
                "complete": _as_bool(item.get("complete")),
                "completed_at": _format_datetime(item.get("timecompleted")),
            }
        )
    return {
        "completed": _as_bool(status.get("completed")),
        "criteria": criteria,
    }


def simplify_courses(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **_pick(
                course,
                "id",
                "shortname",
                "fullname",
                "categoryid",
                "idnumber",
            ),
            "startdate": _format_date(course.get("startdate")),
            "enddate": _format_date(course.get("enddate")),
            "visible": _as_bool(course.get("visible")),
        }
        for course in data
    ]


def simplify_users_courses(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    simplified = []
    for course in data:
        item = _pick(
            course,
            "id",
            "shortname",
            "fullname",
            "idnumber",
            "progress",
        )
        item["startdate"] = _format_date(course.get("startdate"))
        item["enddate"] = _format_date(course.get("enddate"))
        if "category" in course:
            item["categoryid"] = course["category"]
        if "visible" in course:
            item["visible"] = _as_bool(course["visible"])
        simplified.append(item)
    return simplified


def _simplify_user(user: dict[str, Any]) -> dict[str, Any]:
    simplified = _pick(user, "id", "username", "fullname", "email", "idnumber")
    roles = user.get("roles")
    if roles:
        simplified["roles"] = [
            role.get("shortname") or role.get("name") for role in roles
        ]
    groups = user.get("groups")
    if groups:
        simplified["groups"] = [
            {"id": group.get("id"), "name": group.get("name")} for group in groups
        ]
    return simplified


def simplify_enrolled_users(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_simplify_user(user) for user in data]


def simplify_get_users(data: dict[str, Any]) -> dict[str, Any]:
    return {"users": [_simplify_user(user) for user in data.get("users", [])]}


def simplify_course_progress(data: dict[str, Any]) -> dict[str, Any]:
    if "error" in data:
        return data
    progress = data.get("progress")
    return {
        "courseid": data.get("courseid"),
        "userid": data.get("userid"),
        "course": data.get("course"),
        "progress_percent": round(progress, 2) if progress is not None else None,
        "enablecompletion": _as_bool(data.get("enablecompletion")),
    }


def simplify_grade_items(data: dict[str, Any]) -> dict[str, Any]:
    users = []
    for entry in data.get("usergrades", []):
        grades = []
        for item in entry.get("gradeitems", []):
            grades.append(
                {
                    "id": item.get("id"),
                    "name": item.get("itemname"),
                    "type": item.get("itemtype"),
                    "module": item.get("itemmodule"),
                    "grade": item.get("gradeformatted") or item.get("graderaw"),
                    "max": item.get("grademax"),
                    "min": item.get("grademin"),
                    "percentage": item.get("percentageformatted"),
                }
            )
        users.append(
            {
                "userid": entry.get("userid"),
                "user": entry.get("userfullname"),
                "grades": grades,
            }
        )
    return {"users": users}


def _table_cell(row: dict[str, Any], column: str) -> str | None:
    cell = row.get(column)
    if not isinstance(cell, dict):
        return None
    content = cell.get("content")
    if content is None:
        return None
    return _strip_html(str(content)) or None


def simplify_grades_table(data: dict[str, Any]) -> dict[str, Any]:
    tables = []
    for table in data.get("tables", []):
        rows = []
        for row in table.get("tabledata", []):
            item_cell = row.get("itemname")
            if not isinstance(item_cell, dict):
                continue
            item_name = _strip_html(str(item_cell.get("content", "")))
            if not item_name:
                continue
            rows.append(
                {
                    "item": item_name,
                    "grade": _table_cell(row, "grade"),
                    "percentage": _table_cell(row, "percentage"),
                    "range": _table_cell(row, "range"),
                    "feedback": _table_cell(row, "feedback"),
                }
            )
        tables.append(
            {
                "courseid": table.get("courseid"),
                "userid": table.get("userid"),
                "user": table.get("userfullname"),
                "rows": rows,
            }
        )
    return {"tables": tables}


TRANSFORMERS: dict[str, Callable[[Any], Any]] = {
    "core_completion_get_activities_completion_status": simplify_activities_completion,
    "core_completion_get_course_completion_status": simplify_course_completion,
    "core_course_get_courses": simplify_courses,
    "core_enrol_get_enrolled_users": simplify_enrolled_users,
    "core_enrol_get_users_courses": simplify_users_courses,
    "core_user_get_users": simplify_get_users,
    "get_course_progress": simplify_course_progress,
    "core_course_completion_status": simplify_course_progress,
    "gradereport_user_get_grade_items": simplify_grade_items,
    "gradereport_user_get_grades_table": simplify_grades_table,
}


def detect_source(data: Any) -> str | None:
    if isinstance(data, dict):
        if "error" in data:
            return None
        if "tables" in data:
            return "gradereport_user_get_grades_table"
        if "usergrades" in data:
            return "gradereport_user_get_grade_items"
        if "statuses" in data:
            return "core_completion_get_activities_completion_status"
        if "completionstatus" in data:
            return "core_completion_get_course_completion_status"
        if "users" in data:
            return "core_user_get_users"
        if {"courseid", "userid", "progress"} <= data.keys():
            return "get_course_progress"
        if any(_normalize_source(key) in TRANSFORMERS for key in data):
            return "merged"
    if isinstance(data, list) and data:
        sample = data[0]
        if not isinstance(sample, dict):
            return None
        if "email" in sample or "roles" in sample:
            return "core_enrol_get_enrolled_users"
        if "categoryid" in sample:
            return "core_course_get_courses"
        if "progress" in sample or "category" in sample:
            return "core_enrol_get_users_courses"
    return None


def simplify(data: Any, source: str | None = None) -> Any:
    if isinstance(data, dict) and "error" in data:
        return data

    if source:
        transformer = TRANSFORMERS.get(_normalize_source(source))
        if transformer:
            return transformer(data)
        return data

    detected = detect_source(data)
    if detected == "merged":
        return {
            key: simplify(value, _normalize_source(key))
            for key, value in data.items()
            if _normalize_source(key) in TRANSFORMERS
        }

    if detected and detected in TRANSFORMERS:
        return TRANSFORMERS[detected](data)

    return data


def _load_input(path: str | None) -> Any:
    text = sys.stdin.read() if path is None else open(path, encoding="utf-8").read()
    return json.loads(text)


def _dump(data: Any, path: str | None) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as file:
            file.write(payload)
            file.write("\n")
    else:
        print(payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Упрощает JSON-ответы Moodle API (эндпоинты из server.py)."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Входной JSON-файл (если не указан — читает из stdin)",
    )
    parser.add_argument("-o", "--output", help="Выходной JSON-файл (по умолчанию — stdout)")
    parser.add_argument(
        "-s",
        "--source",
        choices=MOODLE_SOURCES,
        help="Имя Moodle API-функции, если автоопределение не сработало",
    )
    args = parser.parse_args()

    data = _load_input(args.input)
    result = simplify(data, args.source)
    _dump(result, args.output)


if __name__ == "__main__":
    main()
