import json

from core.model_transports import (
    BRAIN_RESULT_SCHEMA,
    OllamaTransport,
    OpenAICompatibleChatTransport,
    OpenAIResponsesTransport,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, *, get_response=None, post_response=None):
        self.get_response = get_response
        self.post_response = post_response
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.get_response

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self.post_response


def sample_json():
    return json.dumps({
        "speech": "Fala de teste.",
        "topic": "benefits",
        "used_facts": [],
        "needs_fact": False,
        "next_sales_thread": "usage",
    })


def test_ollama_uses_shared_messages_and_json_schema():
    session = FakeSession(
        post_response=FakeResponse({
            "message": {"content": sample_json()}
        })
    )
    transport = OllamaTransport(
        model="qwen3:4b",
        session=session,
    )
    output = transport.complete(
        system_instruction="SYSTEM AGCN",
        user_payload='{"MODE":"proactive"}',
    )
    assert json.loads(output)["speech"] == "Fala de teste."

    url, kwargs = session.post_calls[0]
    assert url.endswith("/api/chat")
    body = kwargs["json"]
    assert body["model"] == "qwen3:4b"
    assert body["messages"][0]["content"] == "SYSTEM AGCN"
    assert body["messages"][1]["content"] == '{"MODE":"proactive"}'
    assert body["format"] == BRAIN_RESULT_SCHEMA
    assert body["stream"] is False


def test_openai_responses_uses_instructions_and_structured_output():
    response_payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": sample_json(),
                    }
                ],
            }
        ]
    }
    session = FakeSession(
        post_response=FakeResponse(response_payload)
    )
    transport = OpenAIResponsesTransport(
        api_key="test-key",
        model="gpt-test",
        session=session,
    )
    output = transport.complete(
        system_instruction="SYSTEM AGCN",
        user_payload='{"MODE":"comment_reply"}',
    )
    assert json.loads(output)["topic"] == "benefits"

    url, kwargs = session.post_calls[0]
    assert url.endswith("/responses")
    body = kwargs["json"]
    assert body["instructions"] == "SYSTEM AGCN"
    assert body["input"] == '{"MODE":"comment_reply"}'
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["schema"] == BRAIN_RESULT_SCHEMA
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_openai_compatible_chat_uses_same_two_messages():
    session = FakeSession(
        post_response=FakeResponse({
            "choices": [
                {"message": {"content": sample_json()}}
            ]
        })
    )
    transport = OpenAICompatibleChatTransport(
        api_key="abc",
        model="other-model",
        base_url="https://provider.example/v1",
        session=session,
    )
    output = transport.complete(
        system_instruction="POLICY",
        user_payload="TURN",
    )
    assert json.loads(output)["speech"] == "Fala de teste."

    _, kwargs = session.post_calls[0]
    body = kwargs["json"]
    assert body["messages"] == [
        {"role": "system", "content": "POLICY"},
        {"role": "user", "content": "TURN"},
    ]
    assert body["response_format"]["type"] == "json_schema"
