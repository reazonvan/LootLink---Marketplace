"""
Middleware для админ-панели: счётчики sidebar.
"""
from django.core.cache import cache

from listings.models import Report
from transactions.models_disputes import Dispute


SIDEBAR_CACHE_TTL = 60  # секунд


class AdminPanelContextMiddleware:
    """Подкладывает счётчики в request только на маршрутах кастомной админки."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/custom-admin/') and self._is_staff(request.user):
            counters = cache.get('admin_panel:sidebar_counters')
            if counters is None:
                pending_reports = Report.objects.filter(status='pending').count()
                active_disputes = Dispute.objects.filter(
                    status__in=['open', 'under_review']
                ).count()
                counters = {
                    'pending_reports': pending_reports,
                    'active_disputes': active_disputes,
                }
                cache.set('admin_panel:sidebar_counters', counters, SIDEBAR_CACHE_TTL)

            request.pending_moderation = counters['pending_reports']
            request.pending_reports = counters['pending_reports']
            request.active_disputes = counters['active_disputes']

        return self.get_response(request)

    @staticmethod
    def _is_staff(user):
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.is_moderator)
