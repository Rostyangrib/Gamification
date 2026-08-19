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


class RepeatingClient:
    def __init__(self) -> None:
        self.calls = 0

    def chat(self, *, model, messages, tools):
        del model, messages, tools
        self.calls += 1
        return SimpleNamespace(
            message=SimpleNamespace(
                content="",
                tool_calls=[_tool_call("list_users", {})],
            )
        )


class CountingSession(FakeSession):
    def __init__(self) -> None:
        self.calls = 0

    async def call_tool(self, name, args):
        self.calls += 1
        return await super().call_tool(name, args)


def test_agent_stops_before_repeating_identical_tool_call():
    client = RepeatingClient()
    session = CountingSession()

    result, tools_used = asyncio.run(
        run_agent_prompt(
            session,
            client,
            [],
            "Список пользователей",
            model="test-model",
            max_steps=5,
        )
    )

    assert client.calls == 2
    assert session.calls == 1
    assert tools_used == ["list_users"]
    assert result == {"tool": "list_users", "args": {}}


class SingleResponseClient:
    def __init__(self) -> None:
        self.calls = 0

    def chat(self, *, model, messages, tools):
        del model, messages, tools
        self.calls += 1
        if self.calls > 1:
            raise AssertionError("A final tool result must not trigger another LLM request")
        return SimpleNamespace(
            message=SimpleNamespace(
                content="",
                tool_calls=[
                    _tool_call("core_user_get_users", {"key": "email", "value": "%"})
                ],
            )
        )


def test_agent_returns_user_list_without_second_llm_request():
    client = SingleResponseClient()

    result, tools_used = asyncio.run(
        run_agent_prompt(
            FakeSession(),
            client,
            [],
            "Список пользователей Moodle",
            model="test-model",
            max_steps=5,
        )
    )

    assert client.calls == 1
    assert tools_used == ["core_user_get_users"]
    assert result == {
        "tool": "core_user_get_users",
        "args": {"key": "email", "value": "%"},
    }
