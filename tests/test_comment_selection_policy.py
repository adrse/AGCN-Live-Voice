from core.comment_selection_policy import (
    CommentSelectionPolicy,
    is_obvious_noise,
)


def test_noise_is_dropped():
    assert is_obvious_noise("😂😂😂")
    assert is_obvious_noise("oi")
    assert not is_obvious_noise("qual o preço?")


def test_purchase_beats_benefit_question():
    policy = CommentSelectionPolicy()
    purchase = policy.route_local("1", "Maria", "quero comprar, onde clica?")
    question = policy.route_local("2", "Joao", "qual o benefício?")
    assert purchase is not None
    assert question is not None
    chosen = policy.select_next([question, purchase])
    assert chosen is purchase


def test_recent_user_penalty_does_not_hide_purchase():
    policy = CommentSelectionPolicy()
    purchase = policy.route_local("1", "Maria", "como compra?")
    technical = policy.route_local("2", "Joao", "pega wifi?")
    chosen = policy.select_next(
        [technical, purchase],
        recently_answered_users={"maria"},
    )
    assert chosen is purchase
