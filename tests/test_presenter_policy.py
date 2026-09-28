from core.integration_contracts import BrainContext, CommentPayload
from core.presenter_policy import build_system_instruction, build_turn_payload


def test_policy_contains_core_live_rules():
    instruction = build_system_instruction()
    assert "Nunca invente" in instruction
    assert "FALA PROATIVA" in instruction
    assert "RETOMADA APÓS INTERRUPÇÃO" in instruction
    assert "ANTI-REPETIÇÃO" in instruction


def test_turn_payload_contains_selected_comment_and_memory():
    ctx = BrainContext(
        mode="comment_reply",
        comment=CommentPayload(id="1", username="Maria", text="quanto custa?"),
        recent_speeches=["fala anterior"],
        recent_facts=["Preço atual: R$ 59,90"],
        sales_thread="benefícios",
        planner_topic="price",
        allowed_facts=["Preço atual: R$ 59,90"],
    )
    payload = build_turn_payload(ctx)
    assert "Maria" in payload
    assert "quanto custa?" in payload
    assert "fala anterior" in payload
    assert "benefícios" in payload
