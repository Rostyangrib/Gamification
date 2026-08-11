import asyncio
import json
import os
import sys
from pathlib import Path

import ollama
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_agent import run_agent_prompt, to_ollama_tools

load_dotenv()

if sys.platform == "win32" and hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
SERVER = Path(__file__).parent / "server.py"
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "5"))


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
            tools = to_ollama_tools(await session.list_tools())

            print(f"Модель: {MODEL}. Пустая строка — выход.")
            while True:
                prompt = input("\n> ").strip()
                if not prompt:
                    break
                try:
                    data, _ = await run_agent_prompt(
                        session,
                        client,
                        tools,
                        prompt,
                        model=MODEL,
                        max_steps=MAX_STEPS,
                    )
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
