from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.external_service import ExternalService
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.manager import ExternalServiceResponse, MoodleCredentials
from app.services import moodle_client
from app.services.mcp_chat import format_chat_error, run_mcp_prompt

router = APIRouter(prefix="/api", tags=["chat"])


def _service_response(service: ExternalService) -> ExternalServiceResponse:
    return ExternalServiceResponse(
        id=service.id,
        name=service.name,
        url=service.url,
        has_token=bool((service.token or "").strip()),
        login=service.login or "",
        created_at=service.created_at,
    )


def _resolve_service_credentials(db: Session, service_id: int) -> tuple[str, str]:
    service = db.scalar(select(ExternalService).where(ExternalService.id == service_id))
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сервис не найден")

    token = (service.token or "").strip()
    login = (service.login or "").strip()
    password = service.password or ""
    if token:
        creds = MoodleCredentials(url=service.url, credential=token, password="")
    elif login:
        creds = MoodleCredentials(url=service.url, credential=login, password=password)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У сервиса не заданы токен или логин/пароль",
        )

    try:
        resolved = moodle_client.resolve_token(
            creds.url,
            creds.credential,
            creds.password,
            service=creds.service,
        )
    except moodle_client.MoodleClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return creds.url.rstrip("/"), resolved


@router.get("/chat/services", response_model=list[ExternalServiceResponse])
def list_chat_services(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ExternalServiceResponse]:
    services = db.scalars(select(ExternalService).order_by(ExternalService.name)).all()
    return [_service_response(item) for item in services]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    del current_user

    moodle_url, moodle_token = _resolve_service_credentials(db, data.service_id)

    try:
        result, tools_used = await run_mcp_prompt(
            data.message.strip(),
            moodle_url=moodle_url,
            moodle_token=moodle_token,
        )
        return ChatResponse(result=result, tools_used=tools_used)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка MCP/Ollama: {format_chat_error(e)}",
        ) from e
