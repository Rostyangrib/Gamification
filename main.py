import asyncio
import json
import os
import sys
from pathlib import Path

import ollama
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from moodle_simplify import simplify

load_dotenv()

if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
SERVER = Path(__file__).parent / "server.py"
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))


def _safe_text(text: str) -> str:
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def _sanitize(value: object) -> object:
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def _to_ollama_tools(mcp_tools) -> list[dict]:
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


def _merge(names: list[str], results: list[object]) -> object:
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


def _parse_args(arguments: object) -> dict:
    if isinstance(arguments, str):
        return json.loads(arguments)
    return dict(arguments)


def _parse_tool_result(mcp_result, tool_name: str) -> object:
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


async def _call_tool(session: ClientSession, name: str, args: dict) -> tuple[str, object]:
    mcp_result = await session.call_tool(name, args)
    parsed = _parse_tool_result(mcp_result, name)
    simplified = simplify(parsed)
    return json.dumps(simplified, ensure_ascii=False), simplified


async def _run_prompt(
    session: ClientSession, client: ollama.Client, tools: list[dict], prompt: str
) -> object:
    messages: list[object] = [{"role": "user", "content": prompt}]
    last_results: object | None = None

    for _ in range(MAX_STEPS):
        response = client.chat(model=MODEL, messages=messages, tools=tools)
        messages.append(response.message)

        tool_calls = response.message.tool_calls
        if not tool_calls:
            if last_results is not None:
                return last_results
            content = response.message.content or ""
            raise ValueError(content.strip() or "Модель не вызвала ни одного tool")

        names: list[str] = []
        results: list[object] = []
        for call in tool_calls:
            args = _parse_args(call.function.arguments)
            text, parsed = await _call_tool(session, call.function.name, args)
            names.append(call.function.name)
            results.append(_sanitize(parsed))
            messages.append(
                {
                    "role": "tool",
                    "tool_name": call.function.name,
                    "content": _safe_text(text),
                }
            )

        last_results = _sanitize(_merge(names, results))

    return last_results


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env=dict(os.environ),
    )
    client = ollama.Client(host=HOST)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = _to_ollama_tools(await session.list_tools())

            print(f"Модель: {MODEL}. Пустая строка — выход.")
            while True:
                prompt = input("\n> ").strip()
                if not prompt:
                    break
                try:
                    data = await _run_prompt(session, client, tools, prompt)
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
