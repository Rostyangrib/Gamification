from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.external_service import ExternalService
from app.models.user import User, UserRole
from app.schemas.manager import (
    CoursesRequest,
    EmployeeResponse,
    EnrolRequest,
    ExternalServiceCreate,
    ExternalServiceResponse,
    ExternalServiceUpdate,
    MoodleCourseResponse,
    MoodleCredentials,
    UnenrolRequest,
    UserCoursesRequest,
)
from app.services import moodle_client

router = APIRouter(prefix="/api/manager", tags=["manager"])


def require_manager(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для менеджера или администратора",
        )
    return current_user


def _get_service(db: Session, service_id: int) -> ExternalService:
    service = db.scalar(select(ExternalService).where(ExternalService.id == service_id))
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сервис не найден")
    return service


def _credentials_from_service(service: ExternalService) -> MoodleCredentials:
    token = (service.token or "").strip()
    login = (service.login or "").strip()
    password = service.password or ""
    if token:
        return MoodleCredentials(url=service.url, credential=token, password="")
    if login:
        return MoodleCredentials(url=service.url, credential=login, password=password)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="У сервиса не заданы токен или логин/пароль",
    )


def _resolve_moodle(creds: MoodleCredentials) -> tuple[str, str]:
    try:
        token = moodle_client.resolve_token(
            creds.url,
            creds.credential,
            creds.password,
            service=creds.service,
        )
        return creds.url.rstrip("/"), token
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _resolve_service(db: Session, service_id: int) -> tuple[str, str]:
    service = _get_service(db, service_id)
    return _resolve_moodle(_credentials_from_service(service))


def _get_employee(db: Session, user_id: int) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сотрудник неактивен")
    return user


def _moodle_userid(url: str, token: str, employee: User) -> int:
    if employee.moodle_id is not None:
        return int(employee.moodle_id)
    try:
        return moodle_client.find_user_id_by_email(url, token, employee.email)
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{exc}. Укажите moodle_id пользователю в БД или проверьте email в Moodle.",
        ) from exc


def _service_response(service: ExternalService) -> ExternalServiceResponse:
    return ExternalServiceResponse(
        id=service.id,
        name=service.name,
        url=service.url,
        has_token=bool((service.token or "").strip()),
        login=service.login or "",
        created_at=service.created_at,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def list_employees(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[User]:
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .where(User.role.in_([UserRole.EMPLOYEE, UserRole.MANAGER, UserRole.ADMIN]))
        .order_by(User.name)
    ).all()
    return list(users)


@router.get("/services", response_model=list[ExternalServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[ExternalServiceResponse]:
    services = db.scalars(select(ExternalService).order_by(ExternalService.name)).all()
    return [_service_response(item) for item in services]


@router.post("/services", response_model=ExternalServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ExternalServiceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> ExternalServiceResponse:
    url = body.url.strip().rstrip("/")
    name = body.name.strip() or url
    token = body.token.strip()
    login = body.login.strip()
    password = body.password

    # Проверяем, что credentials рабочие, до сохранения
    creds = MoodleCredentials(
        url=url,
        credential=token if token else login,
        password="" if token else password,
    )
    _resolve_moodle(creds)

    existing = db.scalar(select(ExternalService).where(ExternalService.url == url))
    if existing:
        existing.name = name
        existing.token = token
        existing.login = login
        existing.password = password if not token else ""
        db.commit()
        db.refresh(existing)
        return _service_response(existing)

    service = ExternalService(
        name=name,
        url=url,
        token=token,
        login=login,
        password=password if not token else "",
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return _service_response(service)


@router.put("/services/{service_id}", response_model=ExternalServiceResponse)
def update_service(
    service_id: int,
    body: ExternalServiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> ExternalServiceResponse:
    service = _get_service(db, service_id)
    url = body.url.strip().rstrip("/")
    name = body.name.strip() or url

    new_token = body.token.strip()
    new_login = body.login.strip()
    new_password = body.password

    if new_token:
        token = new_token
        login = new_login or service.login
        password = ""
    elif new_login and new_password:
        token = ""
        login = new_login
        password = new_password
    elif new_login and (service.password or "").strip() and not (service.token or "").strip():
        token = ""
        login = new_login
        password = service.password
    else:
        token = service.token or ""
        login = new_login or (service.login or "")
        password = service.password or ""
        if new_password:
            password = new_password
            token = ""

    has_token = bool(token.strip())
    has_login = bool(login.strip()) and bool(password.strip())
    if not has_token and not has_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите токен или пару логин + пароль",
        )

    creds = MoodleCredentials(
        url=url,
        credential=token if has_token else login,
        password="" if has_token else password,
    )
    _resolve_moodle(creds)

    conflict = db.scalar(
        select(ExternalService).where(
            ExternalService.url == url,
            ExternalService.id != service_id,
        )
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Сервис с таким URL уже существует",
        )

    service.name = name
    service.url = url
    service.token = token if has_token else ""
    service.login = login if not has_token else (login or "")
    service.password = password if not has_token else ""
    db.commit()
    db.refresh(service)
    return _service_response(service)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> None:
    service = _get_service(db, service_id)
    db.delete(service)
    db.commit()


@router.post("/moodle/courses", response_model=list[MoodleCourseResponse])
def list_moodle_courses(
    body: CoursesRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[MoodleCourseResponse]:
    url, token = _resolve_service(db, body.service_id)
    try:
        courses = moodle_client.list_courses(url, token)
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [MoodleCourseResponse(**course) for course in courses]


@router.post("/moodle/user-courses", response_model=list[MoodleCourseResponse])
def list_employee_courses(
    body: UserCoursesRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[MoodleCourseResponse]:
    url, token = _resolve_service(db, body.service_id)
    employee = _get_employee(db, body.user_id)
    moodle_userid = _moodle_userid(url, token, employee)
    try:
        courses = moodle_client.list_user_courses(url, token, moodle_userid)
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [MoodleCourseResponse(**course) for course in courses]


@router.post("/moodle/enrol", status_code=status.HTTP_204_NO_CONTENT)
def enrol_employee(
    body: EnrolRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> None:
    url, token = _resolve_service(db, body.service_id)
    employee = _get_employee(db, body.user_id)
    moodle_userid = _moodle_userid(url, token, employee)
    try:
        moodle_client.enrol_user(url, token, moodle_userid, body.course_id)
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/moodle/unenrol", status_code=status.HTTP_204_NO_CONTENT)
def unenrol_employee(
    body: UnenrolRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
) -> None:
    url, token = _resolve_service(db, body.service_id)
    employee = _get_employee(db, body.user_id)
    moodle_userid = _moodle_userid(url, token, employee)
    try:
        moodle_client.unenrol_user(url, token, moodle_userid, body.course_id)
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
