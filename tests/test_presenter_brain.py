import json

import pytest

from core.integration_contracts import BrainContext, CommentPayload
from core.presenter_brain import BrainOutputError, PresenterBrain


class FakeTransport:
    name = "fake"

    def __init__(self, response):
        self.response = response
        self.system_instruction = None
        self.user_payload = None

    def healthcheck(self):
        return True, "ok"

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        self.system_instruction = system_instruction
        self.user_payload = user_payload
        return self.response


def test_presenter_brain_always_injects_shared_policy():
    transport = FakeTransport(json.dumps({
        "speech": "Maria, essa informacao eu nao tenho confirmada agora.",
        "topic": "compatibility",
        "used_facts": [],
        "needs_fact": True,
        "next_sales_thread": "bateria",
    }))
    brain = PresenterBrain(transport)
    context = BrainContext(
        mode="comment_reply",
        comment=CommentPayload(id="1", username="Maria", text="pega internet?"),
        decision={"intent": "technical_question", "priority": 80},
        sales_thread="bateria",
        allowed_facts=["Bateria de ate 7 dias"],
    )

    result = brain.generate(context)

    assert result.needs_fact is True
    assert "Nunca invente" in transport.system_instruction
    assert '"MODE":"comment_reply"' in transport.user_payload
    assert "pega internet?" in transport.user_payload


def test_presenter_brain_rejects_free_text():
    brain = PresenterBrain(FakeTransport("Oi pessoal, olha essa oferta!"))
    with pytest.raises(BrainOutputError):
        brain.generate(BrainContext(mode="proactive"))


def test_presenter_brain_rejects_claimed_facts_without_allowlist():
    transport = FakeTransport(json.dumps({
        "speech": "Tem bateria de 10 dias.",
        "topic": "battery",
        "used_facts": ["Bateria de 10 dias"],
        "needs_fact": False,
        "next_sales_thread": "",
    }))
    brain = PresenterBrain(transport)

    with pytest.raises(BrainOutputError):
        brain.generate(BrainContext(mode="proactive", allowed_facts=[]))
