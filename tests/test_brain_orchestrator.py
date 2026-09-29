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


def test_brain_rejects_price_claim_without_price_fact():
    transport = FakeTransport([
        json.dumps({
            "speech": "Está por R$ 99,90 agora.",
            "topic": "price",
            "used_facts": [],
            "needs_fact": False,
            "next_sales_thread": "",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    try:
        brain.generate(
            BrainContext(
                mode="comment_reply",
                allowed_facts=["nome: Produto X"],
            )
        )
    except BrainOutputError:
        pass
    else:
        raise AssertionError("deveria rejeitar preço inventado")


def test_brain_accepts_price_when_exact_fact_is_reported():
    transport = FakeTransport([
        json.dumps({
            "speech": "Está por R$ 99,90 agora.",
            "topic": "price",
            "used_facts": ["preço atual: R$ 99,90"],
            "needs_fact": False,
            "next_sales_thread": "benefits",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)
    result = brain.generate(
        BrainContext(
            mode="comment_reply",
            allowed_facts=["preço atual: R$ 99,90"],
        )
    )
    assert result.speech == "Está por R$ 99,90 agora."


def test_brain_rejects_unregistered_numeric_specification():
    transport = FakeTransport([
        json.dumps({
            "speech": "A bateria dura 10 dias.",
            "topic": "battery",
            "used_facts": ["bateria/autonomia: até 7 dias"],
            "needs_fact": False,
            "next_sales_thread": "",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    try:
        brain.generate(
            BrainContext(
                mode="comment_reply",
                allowed_facts=["bateria/autonomia: até 7 dias"],
            )
        )
    except BrainOutputError:
        pass
    else:
        raise AssertionError("deveria rejeitar número não autorizado")


def test_needs_fact_does_not_bypass_numeric_validation():
    transport = FakeTransport([
        json.dumps({
            "speech": "A bateria dura 12 dias.",
            "topic": "battery",
            "used_facts": [],
            "needs_fact": True,
            "next_sales_thread": "",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    try:
        brain.generate(
            BrainContext(
                mode="comment_reply",
                allowed_facts=["nome: Produto X"],
            )
        )
    except BrainOutputError:
        pass
    else:
        raise AssertionError(
            "needs_fact não pode liberar número inventado"
        )


def test_brain_retries_when_proactive_opening_repeats():
    fact = "benefícios: áudio claro"
    transport = FakeTransport([
        json.dumps({
            "speech": "Olha esse fone, o áudio claro faz diferença no dia a dia.",
            "topic": "benefits",
            "used_facts": [fact],
            "needs_fact": False,
            "next_sales_thread": "usage",
        }),
        json.dumps({
            "speech": "Pra ouvir no dia a dia, o áudio claro ajuda bastante.",
            "topic": "benefits",
            "used_facts": [fact],
            "needs_fact": False,
            "next_sales_thread": "usage",
        }),
    ])
    brain = PresenterBrain(transport, max_retries=1)
    result = brain.generate(
        BrainContext(
            mode="proactive",
            recent_speeches=[
                "Olha esse fone, a bateria dele ajuda bastante no dia a dia."
            ],
            allowed_facts=[fact],
        )
    )

    assert result.speech.startswith("Pra ouvir")
    assert len(transport.calls) == 2
    assert "fala muito parecida" in transport.calls[1][1]


def test_brain_rejects_fake_scarcity_without_fact():
    transport = FakeTransport([
        json.dumps({
            "speech": "Corre que está acabando!",
            "topic": "scarcity",
            "used_facts": [],
            "needs_fact": False,
            "next_sales_thread": "",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    try:
        brain.generate(
            BrainContext(
                mode="proactive",
                allowed_facts=["nome: Produto X"],
            )
        )
    except BrainOutputError:
        pass
    else:
        raise AssertionError("deveria rejeitar escassez inventada")


def test_brain_accepts_exact_low_stock_scarcity():
    transport = FakeTransport([
        json.dumps({
            "speech": "Agora restam 3 unidades.",
            "topic": "scarcity",
            "used_facts": ["estoque: 3"],
            "needs_fact": False,
            "next_sales_thread": "benefits",
        })
    ])
    brain = PresenterBrain(transport, max_retries=0)

    result = brain.generate(
        BrainContext(
            mode="proactive",
            allowed_facts=["estoque: 3"],
        )
    )
    assert result.speech == "Agora restam 3 unidades."
