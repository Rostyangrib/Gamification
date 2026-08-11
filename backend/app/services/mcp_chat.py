import os
import sys
from pathlib import Path

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import settings

_BACKEND = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND.parent
_CONTAINER_MCP = _BACKEND / "mcp"


def _mcp_dir() -> Path:
    if (_REPO_ROOT / "server.py").is_file():
        return _REPO_ROOT
    if (_CONTAINER_MCP / "server.py").is_file():
        return _CONTAINER_MCP
    raise FileNotFoundError("MCP server files not found (server.py)")


_MCP_DIR = _mcp_dir()
_MCP_SERVER = _MCP_DIR / "server.py"

if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from mcp_agent import run_agent_prompt, to_ollama_tools  # noqa: E402


def format_chat_error(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(format_chat_error(e) for e in exc.exceptions)
    return str(exc)


def _mcp_server_env(moodle_url: str, moodle_token: str) -> dict[str, str]:
    env = dict(os.environ)
    env["MOODLE_URL"] = moodle_url
    env["MOODLE_TOKEN"] = moodle_token
    return env


async def run_mcp_prompt(
    prompt: str,
    *,
    moodle_url: str,
    moodle_token: str,
) -> tuple[object, list[str]]:
    if not moodle_url.strip() or not moodle_token.strip():
        raise ValueError("Не заданы URL или токен Moodle для выбранного сервиса")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_MCP_SERVER)],
        env=_mcp_server_env(moodle_url.rstrip("/"), moodle_token),
    )
    client = ollama.Client(host=settings.ollama_host)
    error: Exception | None = None
    result: tuple[object, list[str]] | None = None

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = to_ollama_tools(await session.list_tools())
            try:
                result = await run_agent_prompt(
                    session,
                    client,
                    tools,
                    prompt,
                    model=settings.ollama_model,
                    max_steps=settings.max_agent_steps,
                )
            except Exception as exc:
                error = exc

    if error is not None:
        raise error
    assert result is not None
    return result
