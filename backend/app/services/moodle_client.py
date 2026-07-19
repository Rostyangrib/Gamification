"""Клиент Moodle Web Services с явными credentials (для страницы Менеджер)."""

from __future__ import annotations

from typing import Any

import httpx


class MoodleClientError(Exception):
    pass


def _flatten_params(prefix: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for key, item in value.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            flat.update(_flatten_params(name, item))
        return flat
    if isinstance(value, list):
        flat: dict[str, Any] = {}
        for index, item in enumerate(value):
            flat.update(_flatten_params(f"{prefix}[{index}]", item))
        return flat
    return {prefix: value}


def _prepare_payload(**params: Any) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            flat.update(_flatten_params(key, value))
        elif value is not None:
            flat[key] = value
    return flat


def resolve_token(
    url: str,
    credential: str,
    password: str = "",
    service: str = "",
) -> str:
    """
    Если password пустой — credential считается токеном.
    Иначе credential = логин, получаем токен через /login/token.php.
    """
    base = url.rstrip("/")
    cred = credential.strip()
    if not base or not cred:
        raise MoodleClientError("Укажите URL и токен или логин Moodle")

    if not password.strip():
        return cred

    services = []
    if service.strip():
        services.append(service.strip())
    # Типичные shortname сервисов в Moodle
    for candidate in ("moodle_mobile_app", "moodle_mobile", "rest_api", "webservice"):
        if candidate not in services:
            services.append(candidate)

    last_error = "Не удалось получить токен Moodle"
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for svc in services:
            payload = {
                "username": cred,
                "password": password,
                "service": svc,
            }
            # Moodle обычно ожидает GET /login/token.php?...
            for method in ("GET", "POST"):
                try:
                    if method == "GET":
                        response = client.get(f"{base}/login/token.php", params=payload)
                    else:
                        response = client.post(f"{base}/login/token.php", data=payload)
                except httpx.HTTPError as exc:
                    last_error = f"Не удалось подключиться к Moodle: {exc}"
                    continue

                try:
                    data = response.json()
                except ValueError:
                    snippet = (response.text or "")[:200]
                    last_error = (
                        f"Moodle вернул не-JSON ответ ({response.status_code}). "
                        f"Проверьте URL. Ответ: {snippet or 'пусто'}"
                    )
                    continue

                if not isinstance(data, dict):
                    last_error = "Неожиданный ответ Moodle при получении токена"
                    continue

                token = data.get("token")
                if token:
                    return str(token)

                error = str(data.get("error") or "")
                code = str(data.get("errorcode") or "")
                last_error = _token_error_message(error, code, svc)

                # Неверный логин — нет смысла перебирать другие сервисы
                if code in {"invalidlogin", "invalid_login"} or "invalid login" in error.lower():
                    raise MoodleClientError(last_error)

    raise MoodleClientError(last_error)


def _token_error_message(error: str, code: str, service: str) -> str:
    hints = {
        "servicenotavailable": (
            f"Сервис «{service}» недоступен. В Moodle: Администрирование → "
            "Плагины → Веб-службы → включите службы и добавьте shortname сервиса "
            "(часто moodle_mobile_app), либо используйте готовый токен вместо логина."
        ),
        "enablewsdescription": (
            "Веб-службы отключены в Moodle. Включите: Администрирование → "
            "Дополнительно → Безопасность → HTTP-безопасность / Веб-службы."
        ),
        "invalidlogin": "Неверный логин или пароль Moodle.",
        "invalid_login": "Неверный логин или пароль Moodle.",
        "userisnotconfirmed": "Учётная запись Moodle не подтверждена.",
        "restoredaccount": "Аккаунт Moodle требует восстановления пароля.",
        "accessexception": "У пользователя нет доступа к веб-службам Moodle.",
    }
    if code in hints:
        return hints[code]
    if error:
        return f"{error}" + (f" ({code})" if code else "")
    if code:
        return f"Ошибка Moodle: {code}"
    return f"Не удалось получить токен через сервис «{service}»"


def call(url: str, token: str, function: str, **params: Any) -> Any:
    base = url.rstrip("/")
    if not base or not token:
        raise MoodleClientError("Задайте URL и токен Moodle")

    payload = {
        "wstoken": token,
        "wsfunction": function,
        "moodlewsrestformat": "json",
        **_prepare_payload(**params),
    }

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.post(f"{base}/webservice/rest/server.php", data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise MoodleClientError(f"Ошибка запроса к Moodle: {exc}") from exc
    except ValueError as exc:
        raise MoodleClientError("Moodle вернул не-JSON ответ") from exc

    if isinstance(data, dict) and data.get("exception"):
        raise MoodleClientError(data.get("message", "Moodle API error"))

    return data


def find_user_id_by_email(url: str, token: str, email: str) -> int:
    data = call(
        url,
        token,
        "core_user_get_users",
        criteria=[{"key": "email", "value": email}],
    )
    users = data.get("users") if isinstance(data, dict) else None
    if not users:
        raise MoodleClientError(f"Пользователь Moodle с email {email} не найден")
    return int(users[0]["id"])


def list_courses(url: str, token: str) -> list[dict[str, Any]]:
    data = call(url, token, "core_course_get_courses")
    if not isinstance(data, list):
        raise MoodleClientError("Неожиданный ответ при получении курсов")
    courses = []
    for course in data:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        if course_id in (None, 1):
            continue
        courses.append(
            {
                "id": int(course_id),
                "fullname": course.get("fullname") or course.get("shortname") or f"Курс {course_id}",
                "shortname": course.get("shortname") or "",
            }
        )
    return courses


def list_user_courses(url: str, token: str, userid: int) -> list[dict[str, Any]]:
    data = call(url, token, "core_enrol_get_users_courses", userid=userid)
    if not isinstance(data, list):
        raise MoodleClientError("Неожиданный ответ при получении курсов пользователя")
    courses = []
    for course in data:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        if course_id is None:
            continue
        courses.append(
            {
                "id": int(course_id),
                "fullname": course.get("fullname") or course.get("shortname") or f"Курс {course_id}",
                "shortname": course.get("shortname") or "",
                "progress": course.get("progress"),
            }
        )
    return courses


def enrol_user(url: str, token: str, userid: int, courseid: int, roleid: int = 5) -> None:
    call(
        url,
        token,
        "enrol_manual_enrol_users",
        enrolments=[
            {
                "roleid": roleid,
                "userid": userid,
                "courseid": courseid,
            }
        ],
    )


def unenrol_user(url: str, token: str, userid: int, courseid: int) -> None:
    call(
        url,
        token,
        "enrol_manual_unenrol_users",
        enrolments=[
            {
                "userid": userid,
                "courseid": courseid,
            }
        ],
    )
