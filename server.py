import json

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Settings as FastMCPSettings

import moodle_api

# mcp 1.29.0 leaves Settings.lifespan as an unresolved forward reference.
# Rebuild after FastMCP has been defined so pydantic-settings can inspect it.
FastMCPSettings.model_rebuild()

mcp = FastMCP("moodle-mcp")


def _out(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _api(function: str, **params: object) -> str:
    try:
        return _out(moodle_api.call(function, **params))
    except Exception as e:
        return _out({"error": str(e)})


@mcp.tool()
def core_completion_get_activities_completion_status(
    courseid: int, userid: int
) -> str:
    """Статус выполнения активностей пользователя в курсе. Параметры: courseid, userid."""
    return _api(
        "core_completion_get_activities_completion_status",
        courseid=courseid,
        userid=userid,
    )


@mcp.tool()
def core_completion_get_course_completion_status(courseid: int, userid: int) -> str:
    """Статус завершения курса для пользователя. Параметры: courseid, userid."""
    return _api(
        "core_completion_get_course_completion_status",
        courseid=courseid,
        userid=userid,
    )


@mcp.tool()
def core_course_get_courses() -> str:
    """Список всех курсов Moodle: id, fullname, shortname. Возвращает информацию по курсу/курсам."""
    return _api("core_course_get_courses")


@mcp.tool()
def core_enrol_get_enrolled_users(courseid: int) -> str:
    """Список записанных на курс пользователей по courseid. Сначала найди courseid через core_course_get_courses."""
    return _api("core_enrol_get_enrolled_users", courseid=courseid)


@mcp.tool()
def core_enrol_get_users_courses(userid: int) -> str:
    """Курсы пользователя по userid. В каждом курсе есть progress (0–100%). Сначала найди userid через core_user_get_users или core_user_get_users_by_field."""
    return _api("core_enrol_get_users_courses", userid=userid)


@mcp.tool()
def get_course_progress(courseid: int, userid: int) -> str:
    """Прогресс / процент выполнения курса для пользователя. Параметры: courseid, userid."""
    try:
        courses = moodle_api.call("core_enrol_get_users_courses", userid=userid)
        for course in courses:
            if course.get("id") == courseid:
                return _out(
                    {
                        "courseid": courseid,
                        "userid": userid,
                        "course": course.get("fullname"),
                        "progress": course.get("progress"),
                        "enablecompletion": course.get("enablecompletion"),
                    }
                )
        return _out(
            {"error": f"User {userid} is not enrolled in course {courseid}"}
        )
    except Exception as e:
        return _out({"error": str(e)})


@mcp.tool()
def core_course_completion_status(courseid: int, userid: int) -> str:
    """Прогресс / процент выполнения курса (то же, что get_course_progress). Параметры: courseid, userid."""
    return get_course_progress(courseid, userid)


@mcp.tool()
def core_user_get_users(key: str, value: str) -> str:
    """Поиск пользователей. key: email, username, firstname, lastname, id, idnumber.
    Чтобы получить всех пользователей: key='email', value='%'."""
    return _api(
        "core_user_get_users",
        criteria=[{"key": key, "value": value}],
    )


@mcp.tool()
def core_user_get_users_by_field(field: str, values: list[str]) -> str:
    """Информация о пользователе по уникальному полю. field: id, idnumber, username, email."""
    return _api(
        "core_user_get_users_by_field",
        field=field,
        values=values,
    )


@mcp.tool()
def gradereport_user_get_grade_items(
    courseid: int, userid: int = 0, groupid: int = 0
) -> str:
    """Полный список элементов оценок пользователей в курсе. Параметры: courseid, userid (0 — все), groupid."""
    return _api(
        "gradereport_user_get_grade_items",
        courseid=courseid,
        userid=userid,
        groupid=groupid,
    )


@mcp.tool()
def gradereport_user_get_grades_table(
    courseid: int, userid: int = 0, groupid: int = 0
) -> str:
    """Таблица оценок пользователя(ей) в курсе. Параметры: courseid, userid (0 — все), groupid."""
    return _api(
        "gradereport_user_get_grades_table",
        courseid=courseid,
        userid=userid,
        groupid=groupid,
    )


if __name__ == "__main__":
    mcp.run()
