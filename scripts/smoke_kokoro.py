from __future__ import annotations

from core.local_kokoro_tts import KokoroLocalTTSProvider


TEXT = (
    "Olha só essa oferta. O produto está cadastrado e eu vou te mostrar "
    "os principais benefícios de forma rápida e direta."
)


def test_profile(profile: str) -> None:
    provider = KokoroLocalTTSProvider(
        profile_id=profile,
        speed=1.28,
    )
    ok, detail = provider.healthcheck()
    if not ok:
        raise RuntimeError(detail)

    chunk = provider.synthesize(TEXT)
    duration = len(chunk.data) / (
        chunk.sample_rate
        * chunk.channels
        * chunk.sample_width
    )
    if duration <= 0.5:
        raise RuntimeError(
            f"Áudio muito curto em {profile}: {duration:.2f}s"
        )

    print(
        f"OK {profile}: "
        f"{chunk.sample_rate} Hz, "
        f"{len(chunk.data)} bytes, "
        f"{duration:.2f}s"
    )


def main() -> int:
    test_profile("female_fast")
    test_profile("male_fast")
    print("Kokoro PT-BR offline: duas vozes aprovadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
