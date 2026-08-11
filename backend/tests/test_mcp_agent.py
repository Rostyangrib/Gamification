import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp_agent import SYSTEM_PROMPT, run_agent_prompt


def _tool_call(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0
        self.messages = []

    def chat(self, *, model, messages, tools):
        del model, tools
        self.messages.append(list(messages))
        responses = [
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[_tool_call("find_user", {"username": "u1"})],
                )
            ),
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[_tool_call("find_courses", {"userid": 42})],
                )
            ),
            SimpleNamespace(
                message=SimpleNamespace(content="готово", tool_calls=[]),
            ),
        ]
        response = responses[self.calls]
        self.calls += 1
        return response


class FakeSession:
    async def call_tool(self, name, args):
        return SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(text=json.dumps({"tool": name, "args": args}))],
        )


def test_agent_uses_system_prompt_and_calls_tools_in_a_loop():
    client = FakeClient()

    result, tools_used = asyncio.run(
        run_agent_prompt(
            FakeSession(),
            client,
            [],
            "Покажи курсы пользователя u1",
            model="test-model",
            max_steps=5,
        )
    )

    assert client.messages[0][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert client.messages[0][1]["role"] == "user"
    assert client.messages[1][-1]["role"] == "tool"
    assert client.messages[2][-1]["tool_name"] == "find_courses"
    assert tools_used == ["find_user", "find_courses"]
    assert result == {"tool": "find_courses", "args": {"userid": 42}}
