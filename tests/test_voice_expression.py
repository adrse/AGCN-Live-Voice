from core.local_qwen3_tts import Qwen3HQLocalTTSProvider
from core.voice_expression import build_voice_instructions, infer_voice_style


def test_expression_maps_sales_contexts():
    assert infer_voice_style({
        "type": "proactive",
        "topic": "scarcity",
        "tactic": "grounded_scarcity",
    }) == "urgent_grounded"

    assert infer_voice_style({
        "type": "reactive",
        "intent": "purchase_confirmation",
    }) == "celebratory"

    assert infer_voice_style({
        "type": "reactive",
        "intent": "objection",
    }) == "reassuring"

    assert infer_voice_style({
        "type": "proactive",
        "topic": "price_value",
        "tactic": "price_anchor",
    }) == "price_confident"


def test_expression_instruction_preserves_base_and_adds_direction():
    style, instruction = build_voice_instructions(
        "Brazilian Portuguese sales presenter.",
        {"topic": "pain_solution", "tactic": "pain_relief"},
        strength=1.0,
    )
    assert style == "empathetic_solution"
    assert "Brazilian Portuguese sales presenter." in instruction
    assert "empathetic" in instruction.casefold()
    assert "do not add new facts" in instruction.casefold()


def test_qwen_provider_changes_style_per_job_without_loading_assets(tmp_path):
    provider = Qwen3HQLocalTTSProvider(
        profile_id="female_fast",
        pack_dir=tmp_path,
        expressive=True,
        expression_strength=1.0,
    )

    style = provider.configure_for_job({
        "type": "proactive",
        "topic": "scarcity",
        "tactic": "grounded_scarcity",
    })
    assert style == "urgent_grounded"
    urgent = provider.active_instructions

    style = provider.configure_for_job({
        "type": "reactive",
        "intent": "objection",
    })
    assert style == "reassuring"
    reassuring = provider.active_instructions

    assert urgent != reassuring
    assert "urgency" in urgent.casefold()
    assert "reassuring" in reassuring.casefold()


def test_qwen_expression_can_be_disabled(tmp_path):
    provider = Qwen3HQLocalTTSProvider(
        profile_id="male_fast",
        pack_dir=tmp_path,
        expressive=False,
    )
    style = provider.configure_for_job({
        "topic": "scarcity",
        "tactic": "grounded_scarcity",
    })
    assert style == "sales_energy"
    assert provider.active_instructions == provider.base_instructions


def test_explicit_suspense_style_is_available():
    style, instruction = build_voice_instructions(
        "Brazilian Portuguese sales presenter.",
        {"voice_style": "suspense_reveal"},
        strength=1.0,
    )
    assert style == "suspense_reveal"
    assert "suspense" in instruction.casefold()
    assert "whisper" in instruction.casefold()
