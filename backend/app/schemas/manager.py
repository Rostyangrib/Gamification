from pydantic import BaseModel, Field, model_validator


class MoodleCredentials(BaseModel):
    url: str = Field(min_length=1, description="URL Moodle")
    credential: str = Field(min_length=1, description="Токен или логин Moodle")
    password: str = Field(default="", description="Пароль (если credential — логин)")
    service: str = Field(default="", description="Shortname веб-службы Moodle")


class ServiceRef(BaseModel):
    service_id: int


class EmployeeResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    department: str
    is_active: bool
    moodle_id: int | None = None

    model_config = {"from_attributes": True}


class MoodleCourseResponse(BaseModel):
    id: int
    fullname: str
    shortname: str = ""
    progress: float | int | None = None


class ExternalServiceCreate(BaseModel):
    name: str = Field(default="", max_length=255)
    url: str = Field(min_length=1, max_length=500)
    token: str = Field(default="")
    login: str = Field(default="")
    password: str = Field(default="")

    @model_validator(mode="after")
    def require_auth(self) -> "ExternalServiceCreate":
        has_token = bool(self.token.strip())
        has_login = bool(self.login.strip()) and bool(self.password.strip())
        if not has_token and not has_login:
            raise ValueError("Укажите токен или пару логин + пароль")
        return self


class ExternalServiceUpdate(BaseModel):
    """Обновление сервиса. Пустые token/password означают «не менять»."""

    name: str = Field(default="", max_length=255)
    url: str = Field(min_length=1, max_length=500)
    token: str = Field(default="")
    login: str = Field(default="")
    password: str = Field(default="")


class ExternalServiceResponse(BaseModel):
    id: int
    name: str
    url: str
    has_token: bool
    login: str
    created_at: object | None = None

    model_config = {"from_attributes": True}


class EnrolRequest(ServiceRef):
    user_id: int
    course_id: int


class UnenrolRequest(ServiceRef):
    user_id: int
    course_id: int


class UserCoursesRequest(ServiceRef):
    user_id: int


class CoursesRequest(ServiceRef):
    pass
