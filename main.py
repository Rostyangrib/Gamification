import asyncio
import json
import os
import sys
from pathlib import Path

import ollama
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
SERVER = Path(__file__).parent / "server.py"


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


async def _run_prompt(
    session: ClientSession, client: ollama.Client, tools: list[dict], prompt: str
) -> object:
    response = client.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
    )

    tool_calls = response.message.tool_calls
    if not tool_calls:
        raise ValueError("Модель не вызвала ни одного tool")

    names: list[str] = []
    results: list[object] = []
    for call in tool_calls:
        args = call.function.arguments
        if isinstance(args, str):
            args = json.loads(args)

        mcp_result = await session.call_tool(call.function.name, args)
        text = mcp_result.content[0].text if mcp_result.content else "{}"
        names.append(call.function.name)
        results.append(json.loads(text))

    return _merge(names, results)


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
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
