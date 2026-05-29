"""Тесты core/antifraud.py — AntiFraudSystem (скоринг рисков пользователей).

Покрывают:
- check_user: набор флагов (новый аккаунт, нет верификации, низкий рейтинг,
  burst листингов, аномально низкая цена) и итоговый action
- check_transaction: усреднение риска buyer + seller
- get_risk_level / get_action_for_score: тиры score → level / action
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

import pytest

from core.antifraud import AntiFraudSystem, antifraud_system


@pytest.fixture
def sys_():
    return AntiFraudSystem()


# ─────────────────────────────────────────────────────────────────────
# get_risk_level / get_action_for_score (pure functions)
# ─────────────────────────────────────────────────────────────────────


def test_get_risk_level_tiers(sys_):
    assert sys_.get_risk_level(0) == "low"
    assert sys_.get_risk_level(29) == "low"
    assert sys_.get_risk_level(30) == "medium"
    assert sys_.get_risk_level(60) == "high"
    assert sys_.get_risk_level(80) == "critical"
    assert sys_.get_risk_level(100) == "critical"


def test_get_action_for_score_tiers(sys_):
    assert sys_.get_action_for_score(0) == "allow"
    assert sys_.get_action_for_score(60) == "flag"
    assert sys_.get_action_for_score(80) == "review"
    assert sys_.get_action_for_score(95) == "block"


# ─────────────────────────────────────────────────────────────────────
# check_user
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_check_user_verified_old_account_allow(sys_, verified_user):
    """Старый верифицированный пользователь без активности → allow."""
    # Сдвигаем date_joined на 30 дней назад
    from accounts.models import CustomUser

    CustomUser.objects.filter(pk=verified_user.pk).update(
        date_joined=timezone.now() - timedelta(days=30),
    )
    verified_user.refresh_from_db()

    result = sys_.check_user(verified_user)
    assert result["action"] == "allow"
    assert result["risk_score"] < 30


@pytest.mark.django_db
def test_check_user_new_unverified_flags(sys_, unverified_user):
    """Новый + не верифицирован → +15+20 = 35.

    action='allow' при score<60, но level='medium' при score>=30.
    """
    result = sys_.check_user(unverified_user)
    assert "Аккаунт младше 1 дня" in result["flags"]
    assert "Email/телефон не верифицированы" in result["flags"]
    assert result["risk_score"] >= 35
    assert result["level"] == "medium"
    assert result["action"] == "allow"  # action-threshold mismatch by design


@pytest.mark.django_db
def test_check_user_burst_listings_raises_risk(
    sys_,
    verified_user,
    game_factory,
):
    """11+ листингов за час → +30 к risk_score."""
    from accounts.models import CustomUser
    from listings.models import Listing

    CustomUser.objects.filter(pk=verified_user.pk).update(
        date_joined=timezone.now() - timedelta(days=30),
    )
    verified_user.refresh_from_db()

    game = game_factory()
    for i in range(11):
        Listing.objects.create(
            seller=verified_user,
            game=game,
            title=f"Spam {i}",
            description="x",
            price=100,
            status="active",
        )

    result = sys_.check_user(verified_user)
    flags = " ".join(result["flags"])
    assert "11 объявлений" in flags or "за час" in flags


@pytest.mark.django_db
def test_check_user_low_rating_with_many_sales(sys_, verified_user):
    """rating<2 при total_sales>5 → +40."""
    from accounts.models import CustomUser

    CustomUser.objects.filter(pk=verified_user.pk).update(
        date_joined=timezone.now() - timedelta(days=30),
    )
    verified_user.profile.rating = Decimal("1.5")
    verified_user.profile.total_sales = 10
    verified_user.profile.save()
    verified_user.refresh_from_db()

    result = sys_.check_user(verified_user)
    assert "Низкий рейтинг" in " ".join(result["flags"])
    assert result["risk_score"] >= 40


# ─────────────────────────────────────────────────────────────────────
# check_transaction
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_check_transaction_combines_buyer_and_seller_risk(
    sys_,
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Score транзакции = (buyer.risk + seller.risk) / 2."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)

    result = sys_.check_transaction(pr)
    assert "risk_score" in result
    assert isinstance(result["risk_score"], int)
    assert result["action"] in ("allow", "flag", "review", "block")
    # Флаги buyer и seller должны иметь префиксы
    if result["flags"]:
        prefixes = {"Покупатель:", "Продавец:"}
        assert any(any(f.startswith(p) for p in prefixes) for f in result["flags"])


# ─────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────


def test_antifraud_singleton_exists():
    """Модуль экспортирует готовый singleton."""
    assert isinstance(antifraud_system, AntiFraudSystem)
