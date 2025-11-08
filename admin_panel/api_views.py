"""
API endpoints для админ-панели (AJAX операции)
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta

from accounts.models import CustomUser, Profile
from listings.models import Listing
from transactions.models import PurchaseRequest
from transactions.models_disputes import Dispute
from listings.models_reports import ListingReport
from core.models_audit import SecurityAuditLog


def is_staff_or_moderator(user):
    """Проверка прав"""
    return user.is_staff or (hasattr(user, 'profile') and user.profile.is_moderator)


def json_response(success=True, message='', data=None):
    """Стандартный JSON ответ"""
    response = {
        'success': success,
        'message': message,
    }
    if data:
        response['data'] = data
    return JsonResponse(response)


# ═══════════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════

@require_POST
@user_passes_test(is_staff_or_moderator)
def verify_user(request, user_id):
    """Верификация пользователя"""
    user = get_object_or_404(CustomUser, id=user_id)
    profile = user.profile
    
    profile.is_verified = not profile.is_verified
    profile.save()
    
    # Логируем действие
    SecurityAuditLog.objects.create(
        user=user,
        action_type='admin_action',
        risk_level='low',
        description=f'Верификация {"включена" if profile.is_verified else "отключена"} администратором {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(
        success=True,
        message=f'Пользователь {"верифицирован" if profile.is_verified else "снята верификация"}',
        data={'is_verified': profile.is_verified}
    )


@require_POST
@staff_member_required
def ban_user(request, user_id):
    """Блокировка пользователя"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if user.is_superuser:
        return json_response(False, 'Нельзя заблокировать владельца')
    
    user.is_active = False
    user.save()
    
    # Логируем
    SecurityAuditLog.objects.create(
        user=user,
        action_type='user_banned',
        risk_level='high',
        description=f'Пользователь заблокирован администратором {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Пользователь заблокирован')


@require_POST
@staff_member_required
def unban_user(request, user_id):
    """Разблокировка пользователя"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    user.is_active = True
    user.save()
    
    SecurityAuditLog.objects.create(
        user=user,
        action_type='admin_action',
        risk_level='low',
        description=f'Пользователь разблокирован администратором {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Пользователь разблокирован')


@require_POST
@staff_member_required
def toggle_moderator(request, user_id):
    """Назначить/снять модератора"""
    user = get_object_or_404(CustomUser, id=user_id)
    profile = user.profile
    
    profile.is_moderator = not profile.is_moderator
    profile.save()
    
    SecurityAuditLog.objects.create(
        user=user,
        action_type='role_changed',
        risk_level='medium',
        description=f'Статус модератора {"назначен" if profile.is_moderator else "снят"} администратором {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(
        success=True,
        message=f'Пользователь {"назначен модератором" if profile.is_moderator else "снят с модерации"}',
        data={'is_moderator': profile.is_moderator}
    )


# ═══════════════════════════════════════════════════════════════
# ОБЪЯВЛЕНИЯ
# ═══════════════════════════════════════════════════════════════

@require_POST
@user_passes_test(is_staff_or_moderator)
def approve_listing(request, listing_id):
    """Одобрить объявление"""
    listing = get_object_or_404(Listing, id=listing_id)
    
    listing.status = 'active'
    listing.save()
    
    # Уведомление продавцу можно добавить
    
    return json_response(True, 'Объявление одобрено и опубликовано')


@require_POST
@user_passes_test(is_staff_or_moderator)
def reject_listing(request, listing_id):
    """Отклонить объявление"""
    listing = get_object_or_404(Listing, id=listing_id)
    reason = request.POST.get('reason', '')
    
    listing.status = 'rejected'
    listing.save()
    
    # Логируем
    SecurityAuditLog.objects.create(
        user=listing.seller,
        action_type='content_moderated',
        risk_level='medium',
        description=f'Объявление "{listing.title}" отклонено модератором. Причина: {reason}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Объявление отклонено')


@require_POST
@staff_member_required
def delete_listing(request, listing_id):
    """Удалить объявление"""
    listing = get_object_or_404(Listing, id=listing_id)
    title = listing.title
    seller = listing.seller
    
    listing.delete()
    
    # Логируем
    SecurityAuditLog.objects.create(
        user=seller,
        action_type='content_deleted',
        risk_level='high',
        description=f'Объявление "{title}" удалено администратором {request.user.username}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Объявление удалено')


# ═══════════════════════════════════════════════════════════════
# ТРАНЗАКЦИИ
# ═══════════════════════════════════════════════════════════════

@require_POST
@staff_member_required
def cancel_transaction(request, transaction_id):
    """Отменить транзакцию (только админ)"""
    transaction = get_object_or_404(PurchaseRequest, id=transaction_id)
    reason = request.POST.get('reason', 'Отменено администратором')
    
    if transaction.status == 'completed':
        return json_response(False, 'Нельзя отменить завершенную сделку')
    
    transaction.status = 'cancelled'
    transaction.save()
    
    # Логируем
    SecurityAuditLog.objects.create(
        user=transaction.buyer,
        action_type='admin_action',
        risk_level='high',
        description=f'Транзакция #{transaction.id} отменена администратором. Причина: {reason}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Транзакция отменена')


# ═══════════════════════════════════════════════════════════════
# СПОРЫ
# ═══════════════════════════════════════════════════════════════

@require_POST
@staff_member_required
def resolve_dispute(request, dispute_id):
    """Разрешить спор"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    resolution = request.POST.get('resolution')
    winner = request.POST.get('winner')  # 'buyer' or 'seller'
    
    if not resolution or not winner:
        return json_response(False, 'Укажите решение и победителя')
    
    dispute.status = 'resolved'
    dispute.resolution = resolution
    dispute.resolved_by = request.user
    dispute.resolved_at = timezone.now()
    dispute.save()
    
    # Логируем
    SecurityAuditLog.objects.create(
        user=request.user,
        action_type='dispute_resolved',
        risk_level='medium',
        description=f'Спор #{dispute.id} разрешен в пользу {winner}. Решение: {resolution}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return json_response(True, 'Спор разрешен')


# ═══════════════════════════════════════════════════════════════
# РЕПОРТЫ
# ═══════════════════════════════════════════════════════════════

@require_POST
@user_passes_test(is_staff_or_moderator)
def process_report(request, report_id):
    """Обработать жалобу"""
    report = get_object_or_404(ListingReport, id=report_id)
    action = request.POST.get('action')  # 'approve', 'reject'
    
    if action == 'approve':
        # Жалоба обоснована - блокируем объявление
        report.listing.status = 'blocked'
        report.listing.save()
        report.status = 'resolved'
        report.admin_notes = f'Обработано модератором {request.user.username}'
        report.save()
        message = 'Жалоба обоснована, объявление заблокировано'
    elif action == 'reject':
        # Жалоба необоснована
        report.status = 'rejected'
        report.admin_notes = f'Отклонено модератором {request.user.username}'
        report.save()
        message = 'Жалоба отклонена'
    else:
        return json_response(False, 'Неверное действие')
    
    return json_response(True, message)


# ═══════════════════════════════════════════════════════════════
# СТАТИСТИКА
# ═══════════════════════════════════════════════════════════════

@user_passes_test(is_staff_or_moderator)
def get_stats(request):
    """Получить статистику для графиков"""
    period = request.GET.get('period', '7')  # days
    
    try:
        days = int(period)
    except ValueError:
        days = 7
    
    today = timezone.now().date()
    start_date = today - timedelta(days=days-1)
    
    # Регистрации
    registrations = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        count = CustomUser.objects.filter(date_joined__date=date).count()
        registrations.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    # Объявления
    listings = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        count = Listing.objects.filter(created_at__date=date).count()
        listings.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    # Сделки
    transactions = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        count = PurchaseRequest.objects.filter(
            created_at__date=date,
            status='completed'
        ).count()
        transactions.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    return json_response(
        success=True,
        data={
            'registrations': registrations,
            'listings': listings,
            'transactions': transactions,
        }
    )

