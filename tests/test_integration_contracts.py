from core.integration_contracts import (
    AudioChunk,
    BrainContext,
    BrainResult,
    CommentPayload,
)
from core.presenter_policy import build_system_instruction, build_turn_payload


def test_contract_dataclasses_are_constructible():
    comment = CommentPayload(id="1", username="Maria", text="quais benefícios?")
    ctx = BrainContext(
        mode="comment_reply",
        comment=comment,
        decision={"intent": "benefits", "priority": 84},
        allowed_facts=["Bateria de 7 dias", "Tela AMOLED"],
    )
    result = BrainResult(
        speech="Maria, ela tem tela AMOLED e bateria de até 7 dias.",
        topic="benefits",
        used_facts=["Tela AMOLED", "Bateria de 7 dias"],
    )
    audio = AudioChunk(data=b"\x00\x00", sample_rate=24000)

    assert ctx.comment is comment
    assert result.speech
    assert audio.sample_rate == 24000


def test_presenter_policy_is_provider_agnostic_and_grounded():
    ctx = BrainContext(
        mode="comment_reply",
        comment=CommentPayload(id="2", username="Joana", text="é à prova d'água?"),
        decision={"intent": "technical_question", "priority": 80},
        recent_speeches=["Olha a bateria desse modelo."],
        sales_thread="bateria",
        planner_topic="compatibility",
        allowed_facts=["Bateria de até 7 dias"],
    )

    system = build_system_instruction()
    payload = build_turn_payload(ctx)

    assert "Qwen" not in system
    assert "OpenAI" not in system
    assert "Nunca invente" in system
    assert "ALLOWED_FACTS" in system
    assert "à prova d'água" in payload
    assert "Bateria de até 7 dias" in payload
    assert '"SALES_THREAD":"bateria"' in payload
