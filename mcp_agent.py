import asyncio
import json
from typing import Any

from moodle_simplify import simplify

SYSTEM_PROMPT = """Ты ассистент Moodle. Отвечай только вызовом tools — никогда не задавай уточняющих вопросов.

Правила интерпретации идентификаторов (если поле не указано явно):
- Пользователь: только цифры (например, 42) → ID, иначе → username (включая u1, ivanov, user_01).
- Курс: только цифры (например, 5) → ID, иначе → shortname (включая MATH101, course1).
"""


def safe_text(text: str) -> str:
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def sanitize(value: object) -> object:
    if isinstance(value, str):
        return safe_text(value)
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def to_ollama_tools(mcp_tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
                or {"type": "object", "properties": {}},
            },
        }
        for tool in mcp_tools.tools
    ]


def merge(names: list[str], results: list[object]) -> object:
    if len(results) == 1:
        return results[0]
    merged: dict[str, object] = {}
    for name, result in zip(names, results):
        key = name
        if key in merged:
            i = 2
            while f"{key}_{i}" in merged:
                i += 1
            key = f"{key}_{i}"
        merged[key] = result
    return merged


def parse_args(arguments: object) -> dict:
    if isinstance(arguments, str):
        return json.loads(arguments)
    return dict(arguments)


def parse_tool_result(mcp_result, tool_name: str) -> object:
    if mcp_result.isError:
        message = next(
            (
                item.text
                for item in mcp_result.content or []
                if getattr(item, "text", None)
            ),
            f"Tool {tool_name} failed",
        )
        return {"error": message}

    text = next(
        (
            item.text
            for item in mcp_result.content or []
            if getattr(item, "text", None)
        ),
        "",
    )
    if not text.strip():
        return {"error": f"Tool {tool_name} returned empty response"}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": text}


async def call_tool(session, name: str, args: dict) -> tuple[str, object]:
    mcp_result = await session.call_tool(name, args)
    parsed = parse_tool_result(mcp_result, name)
    simplified = simplify(parsed)
    return json.dumps(simplified, ensure_ascii=False), simplified


async def run_agent_prompt(
    session,
    client,
    tools: list[dict],
    prompt: str,
    *,
    model: str,
    max_steps: int,
) -> tuple[object, list[str]]:
    messages: list[object] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    last_results: object | None = None
    tools_used: list[str] = []
    no_tool_retries = 0

    for _ in range(max_steps):
        response = await asyncio.to_thread(
            client.chat,
            model=model,
            messages=messages,
            tools=tools,
        )
        messages.append(response.message)

        tool_calls = response.message.tool_calls
        if not tool_calls:
            if last_results is not None:
                return last_results, tools_used
            if no_tool_retries == 0:
                no_tool_retries += 1
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Не уточняй у пользователя. Сразу вызови подходящий tool, "
                            "интерпретируя идентификаторы по правилам из system prompt."
                        ),
                    }
                )
                continue
            content = response.message.content or ""
            raise ValueError(content.strip() or "Модель не вызвала ни одного tool")

        names: list[str] = []
        results: list[object] = []
        for call in tool_calls:
            args = parse_args(call.function.arguments)
            text, parsed = await call_tool(session, call.function.name, args)
            names.append(call.function.name)
            tools_used.append(call.function.name)
            results.append(sanitize(parsed))
            messages.append(
                {
                    "role": "tool",
                    "tool_name": call.function.name,
                    "content": safe_text(text),
                }
            )

        last_results = sanitize(merge(names, results))

    return last_results, tools_used
