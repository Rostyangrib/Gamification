import json
import sys
from pathlib import Path
from typing import Any

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import settings

_MCP_SERVER = Path(__file__).resolve().parents[1] / "mcp_server" / "server.py"


def _to_ollama_tools(mcp_tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
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


async def run_mcp_prompt(prompt: str) -> tuple[object, list[str]]:
    params = StdioServerParameters(command=sys.executable, args=[str(_MCP_SERVER)])
    client = ollama.Client(host=settings.ollama_host)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = _to_ollama_tools(await session.list_tools())

            response = client.chat(
                model=settings.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
            )

            tool_calls = response.message.tool_calls
            if not tool_calls:
                content = response.message.content or ""
                if content.strip():
                    return {"message": content.strip()}, []
                raise ValueError("Модель не вызвала ни одного tool и не вернула текст")

            names: list[str] = []
            results: list[object] = []
            for call in tool_calls:
                args = call.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)

                mcp_result = await session.call_tool(call.function.name, args)
                text = mcp_result.content[0].text if mcp_result.content else "{}"
                names.append(call.function.name)
                try:
                    results.append(json.loads(text))
                except json.JSONDecodeError:
                    results.append({"raw": text})

            return _merge(names, results), names
