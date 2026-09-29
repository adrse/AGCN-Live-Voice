from core.tiktok_monitor import local_clock_text


def test_tiktok_comment_clock_does_not_require_iana_tzdata():
    value = local_clock_text()
    parts = value.split(":")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
