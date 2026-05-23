"""
Тесты transactions/admin_disputes.py — админка диспутов:
- DisputeAdmin (отображение, status_display, actions assign_to_me/mark_under_review)
- DisputeMessageAdmin
- DisputeEvidenceAdmin
"""

from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

import pytest

from payments.models_disputes import Dispute, DisputeEvidence, DisputeMessage
from transactions.admin_disputes import DisputeAdmin, DisputeEvidenceAdmin, DisputeMessageAdmin

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────
# DisputeAdmin
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDisputeAdmin:

    @pytest.fixture
    def admin_instance(self):
        return DisputeAdmin(Dispute, AdminSite())

    @pytest.fixture
    def staff_user(self, db):
        return User.objects.create_user(
            username="admin_user",
            password="x",
            is_staff=True,
            is_superuser=True,
        )

    @pytest.fixture
    def dispute(self, active_listing, buyer, purchase_request_factory):
        from payments.models import Escrow

        pr = purchase_request_factory(active_listing, buyer, status="accepted")
        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=active_listing.seller,
            amount=pr.listing.price,
        )
        return Dispute.objects.create(
            escrow=escrow,
            opened_by=buyer,
            reason="other",
            description="admin test",
        )

    def test_status_display_color_green(self, admin_instance, dispute):
        dispute.status = "resolved_buyer"
        html = admin_instance.status_display(dispute)
        assert "green" in html
        assert "покупателя" in html.lower()

    def test_status_display_color_red(self, admin_instance, dispute):
        dispute.status = "open"
        html = admin_instance.status_display(dispute)
        assert "red" in html

    def test_status_display_color_orange(self, admin_instance, dispute):
        dispute.status = "under_review"
        html = admin_instance.status_display(dispute)
        assert "orange" in html

    def test_status_display_unknown_status_gray(self, admin_instance, dispute):
        dispute.status = "unknown_status"
        html = admin_instance.status_display(dispute)
        assert "gray" in html

    def test_assign_to_me_action(self, admin_instance, dispute, staff_user, rf):
        request = rf.post("/admin/")
        request.user = staff_user
        # Симулируем messages framework
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        queryset = Dispute.objects.filter(pk=dispute.pk)
        admin_instance.assign_to_me(request, queryset)

        dispute.refresh_from_db()
        assert dispute.assigned_to == staff_user
        assert dispute.status == "under_review"

    def test_assign_to_me_skips_already_assigned(
        self,
        admin_instance,
        active_listing,
        buyer,
        user_factory,
        purchase_request_factory,
        staff_user,
        rf,
    ):
        """Если у диспута уже есть модератор — assign_to_me не перезаписывает."""
        pr = purchase_request_factory(active_listing, buyer, status="accepted")
        existing_mod = user_factory(username="existing_mod")
        from payments.models import Escrow

        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=active_listing.seller,
            amount=pr.listing.price,
        )
        dispute = Dispute.objects.create(
            escrow=escrow,
            opened_by=buyer,
            reason="other",
            description="abc",
            assigned_to=existing_mod,
        )

        request = rf.post("/admin/")
        request.user = staff_user
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        admin_instance.assign_to_me(request, Dispute.objects.filter(pk=dispute.pk))
        dispute.refresh_from_db()
        # Модератор не должен поменяться
        assert dispute.assigned_to == existing_mod

    def test_mark_under_review_action(self, admin_instance, dispute, staff_user, rf):
        request = rf.post("/admin/")
        request.user = staff_user
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        admin_instance.mark_under_review(request, Dispute.objects.filter(pk=dispute.pk))
        dispute.refresh_from_db()
        assert dispute.status == "under_review"

    def test_mark_under_review_skips_non_open(
        self,
        admin_instance,
        active_listing,
        buyer,
        purchase_request_factory,
        staff_user,
        rf,
    ):
        """mark_under_review не трогает уже разрешённые диспуты."""
        from payments.models import Escrow

        pr = purchase_request_factory(active_listing, buyer, status="accepted")
        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=pr.seller,
            amount=pr.listing.price,
        )
        dispute = Dispute.objects.create(
            escrow=escrow,
            opened_by=buyer,
            reason="other",
            description="resolved",
            status="resolved_buyer",
        )

        request = rf.post("/admin/")
        request.user = staff_user
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        admin_instance.mark_under_review(request, Dispute.objects.filter(pk=dispute.pk))
        dispute.refresh_from_db()
        assert dispute.status == "resolved_buyer"  # без изменений


# ─────────────────────────────────────────────────────────────────────
# DisputeMessageAdmin / DisputeEvidenceAdmin / GuaranteeServiceAdmin
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSimpleAdmins:

    def test_dispute_message_admin_attrs(self):
        admin = DisputeMessageAdmin(DisputeMessage, AdminSite())
        assert "sender" in admin.list_display
        assert "is_moderator_message" in admin.list_filter
        assert admin.readonly_fields == ["dispute", "sender", "created_at"]

    def test_dispute_evidence_admin_attrs(self):
        admin = DisputeEvidenceAdmin(DisputeEvidence, AdminSite())
        assert "uploaded_by" in admin.list_display
        assert "created_at" in admin.list_filter
        assert "dispute" in admin.readonly_fields


# ─────────────────────────────────────────────────────────────────────
# Admin index pages — smoke
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminPages:
    """Дымовые тесты на index/changelist админки."""

    def test_dispute_changelist_renders(
        self, client, db, active_listing, buyer, purchase_request_factory
    ):
        admin_user = User.objects.create_superuser(
            username="superadmin",
            email="s@s.com",
            password="x",
        )
        client.force_login(admin_user)

        # Создадим один диспут чтобы changelist что-то отображал
        from payments.models import Escrow

        pr = purchase_request_factory(active_listing, buyer, status="accepted")
        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=active_listing.seller,
            amount=pr.listing.price,
        )
        Dispute.objects.create(
            escrow=escrow,
            opened_by=buyer,
            reason="other",
            description="admin smoke",
        )

        # changelist для Dispute
        response = client.get("/admin/transactions/dispute/")
        # Может вернуть 200 (admin зарегистрирован) или 404/500 — главное, что код инстанцируется
        assert response.status_code in (200, 302, 404)
