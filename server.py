import json

from mcp.server.fastmcp import FastMCP

import moodle_api

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
    """Return the activities completion status for a user in a course."""
    return _api(
        "core_completion_get_activities_completion_status",
        courseid=courseid,
        userid=userid,
    )


@mcp.tool()
def core_completion_get_course_completion_status(courseid: int, userid: int) -> str:
    """Returns course completion status."""
    return _api(
        "core_completion_get_course_completion_status",
        courseid=courseid,
        userid=userid,
    )


@mcp.tool()
def core_course_get_courses() -> str:
    """Return all Moodle courses."""
    return _api("core_course_get_courses")


@mcp.tool()
def core_enrol_get_enrolled_users(courseid: int) -> str:
    """Get enrolled users by course id."""
    return _api("core_enrol_get_enrolled_users", courseid=courseid)


@mcp.tool()
def core_enrol_get_users_courses(userid: int) -> str:
    """Get the list of courses where a user is enrolled in."""
    return _api("core_enrol_get_users_courses", userid=userid)


@mcp.tool()
def core_user_get_users(key: str, value: str) -> str:
    """Search for users. key: email, username, firstname, lastname, id, idnumber."""
    return _api(
        "core_user_get_users",
        criteria=[{"key": key, "value": value}],
    )


@mcp.tool()
def gradereport_user_get_grade_items(
    courseid: int, userid: int = 0, groupid: int = 0
) -> str:
    """Returns the complete list of grade items for users in a course."""
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
    """Get the user/s report grades table for a course."""
    return _api(
        "gradereport_user_get_grades_table",
        courseid=courseid,
        userid=userid,
        groupid=groupid,
    )


if __name__ == "__main__":
    mcp.run()
