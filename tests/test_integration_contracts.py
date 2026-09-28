from core.integration_contracts import (
    AudioChunk,
    BrainContext,
    BrainResult,
    CommentPayload,
    MediaClip,
)


def test_contract_dataclasses_are_constructible():
    comment = CommentPayload(id="1", username="Maria", text="quais benefícios?")
    ctx = BrainContext(
        mode="comment_reply",
        comment=comment,
        allowed_facts=["Bateria de 7 dias", "Tela AMOLED"],
    )
    result = BrainResult(
        speech="Maria, ela tem tela AMOLED e bateria de até 7 dias.",
        topic="benefits",
        used_facts=["Tela AMOLED", "Bateria de 7 dias"],
    )
    audio = AudioChunk(data=b"\x00\x00", sample_rate=24000)
    clip = MediaClip(path="produto.mp4")

    assert ctx.comment is comment
    assert result.speech
    assert audio.sample_rate == 24000
    assert clip.muted is True
