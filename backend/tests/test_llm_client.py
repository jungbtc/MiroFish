from types import SimpleNamespace

import app.utils.llm_client as llm_client_module
from app.utils.llm_client import LLMClient


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"ok": true}'),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                completion_tokens_details=SimpleNamespace(reasoning_tokens=3),
            ),
        )


class FakeOpenAIClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class RaisingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("boom")


class RaisingOpenAIClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=RaisingCompletions())


class CapturingLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(message % args)

    def error(self, message, *args):
        self.messages.append(message % args)


def test_chat_payload_includes_selected_reasoning_effort():
    fake_client = FakeOpenAIClient()
    client = LLMClient(
        api_key="sk-test",
        model="gpt-5.4-nano",
        reasoning_effort="high",
    )
    client.client = fake_client

    client.chat([{"role": "user", "content": "hi"}])

    assert fake_client.completions.kwargs["model"] == "gpt-5.4-nano"
    assert fake_client.completions.kwargs["reasoning_effort"] == "high"


def test_chat_payload_omits_custom_temperature_for_gpt5_models():
    fake_client = FakeOpenAIClient()
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5.4-mini",
        reasoning_effort="low",
    )
    client.client = fake_client

    client.chat([{"role": "user", "content": "hi"}], temperature=0.3)

    assert "temperature" not in fake_client.completions.kwargs


def test_chat_payload_expands_completion_budget_for_xhigh_reasoning():
    fake_client = FakeOpenAIClient()
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5.4-mini",
        reasoning_effort="xhigh",
    )
    client.client = fake_client

    client.chat([{"role": "user", "content": "hi"}], max_tokens=4096)

    assert fake_client.completions.kwargs["max_completion_tokens"] == 24576
    assert "max_tokens" not in fake_client.completions.kwargs


def test_chat_json_caps_xhigh_reasoning_effort_for_structured_output():
    fake_client = FakeOpenAIClient()
    client = LLMClient(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-5.4-mini",
        reasoning_effort="xhigh",
    )
    client.client = fake_client

    client.chat_json([{"role": "user", "content": "hi"}])

    assert fake_client.completions.kwargs["reasoning_effort"] == "low"
    assert fake_client.completions.kwargs["max_completion_tokens"] == 8192


def test_llm_logs_include_model_reasoning_and_reasoning_tokens(monkeypatch):
    fake_client = FakeOpenAIClient()
    fake_logger = CapturingLogger()
    monkeypatch.setattr(llm_client_module, "logger", fake_logger)
    client = LLMClient(
        api_key="sk-test",
        model="gpt-5.4-mini",
        reasoning_effort="medium",
    )
    client.client = fake_client

    client.chat([{"role": "user", "content": "hi"}])

    messages = "\n".join(fake_logger.messages)
    assert "LLM request start: model=gpt-5.4-mini, reasoning_effort=medium" in messages
    assert "LLM request complete: model=gpt-5.4-mini, reasoning_effort=medium" in messages
    assert "'reasoning_tokens': 3" in messages


def test_llm_error_log_includes_model_and_reasoning_effort(monkeypatch):
    fake_logger = CapturingLogger()
    monkeypatch.setattr(llm_client_module, "logger", fake_logger)
    client = LLMClient(
        api_key="sk-test",
        model="gpt-5.4-mini",
        reasoning_effort="xhigh",
    )
    client.client = RaisingOpenAIClient()

    try:
        client.chat([{"role": "user", "content": "hi"}])
    except RuntimeError:
        pass

    messages = "\n".join(fake_logger.messages)
    assert "LLM request error: model=gpt-5.4-mini, reasoning_effort=xhigh" in messages
