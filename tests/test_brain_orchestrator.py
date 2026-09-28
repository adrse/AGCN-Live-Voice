import json

from core.brain_orchestrator import BrainOutputError, PresenterBrain
from core.integration_contracts import BrainContext


class FakeTransport:
    name = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def healthcheck(self):
        return True, "ok"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        self.calls.append((system_instruction, user_payload))
        return self.responses.pop(0)


def test_brain_uses_shared_policy_and_parses_json():
    transport = FakeTransport([
        json.dumps({
            "speech": "Ela tem bateria de 7 dias.",
            "topic": "battery",
            "used_facts": ["Bateria de 7 dias"],
            "needs_fact": False,
            "next_sales_thread": "benefícios",
        })
    ])
    brain = PresenterBrain(transport)
    ctx = BrainContext(
        mode="comment_reply",
        allowed_facts=["Bateria de 7 dias"],
    )
    result = brain.generate(ctx)

    assert result.speech == "Ela tem bateria de 7 dias."
    assert "Presenter Brain do AGCN Live Voice" in transport.calls[0][0]
    assert '"MODE":"comment_reply"' in transport.calls[0][1]


def test_brain_retries_invalid_json():
    transport = FakeTransport([
        "texto solto",
        json.dumps({
            "speech": "Não tenho essa informação confirmada.",
            "topic": "technical",
            "used_facts": [],
            "needs_fact": True,
            "next_sales_thread": "",
        }),
    ])
    brain = PresenterBrain(transport, max_retries=1)
    result = brain.generate(BrainContext(mode="comment_reply"))
    assert result.needs_fact is True
    assert len(transport.calls) == 2


def test_brain_rejects_reported_unapproved_fact():
    transport = FakeTransport([
        json.dumps({
            "speech": "É à prova d'água.",
            "topic": "safety",
            "used_facts": ["IP68"],
            "needs_fact": False,
            "next_sales_thread": "",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    try:
        brain.generate(BrainContext(mode="comment_reply", allowed_facts=[]))
    except BrainOutputError:
        pass
    else:
        raise AssertionError("deveria rejeitar fato não autorizado")
