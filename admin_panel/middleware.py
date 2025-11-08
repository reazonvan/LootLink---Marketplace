"""
Middleware для админ-панели
Добавляет счетчики в контекст для sidebar
"""
from listings.models import Listing, Report
from transactions.models_disputes import Dispute


class AdminPanelContextMiddleware:
    """
    Добавляет счетчики для sidebar во все запросы админ-панели
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Добавляем счетчики только для админ-панели
        if request.path.startswith('/custom-admin/'):
            if request.user.is_authenticated and (request.user.is_staff or 
                (hasattr(request.user, 'profile') and request.user.profile.is_moderator)):
                
                request.pending_moderation = Listing.objects.filter(status='pending').count()
                request.pending_reports = Report.objects.filter(status='pending').count()
                request.active_disputes = Dispute.objects.filter(
                    status__in=['pending', 'in_review']
                ).count()
        
        response = self.get_response(request)
        return response

