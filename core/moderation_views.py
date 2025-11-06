"""
Views для модерации.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from listings.models import Report
from .moderation_models import UserBan, UserWarning, ModerationQueue, AutoModeration
from accounts.models import CustomUser
from django.utils import timezone


def is_moderator(user):
    """Проверка что пользователь - модератор"""
    return user.is_staff or (hasattr(user, 'profile') and user.profile.is_moderator)


@login_required
@user_passes_test(is_moderator)
def moderation_dashboard(request):
    """Дашборд модератора"""
    # Статистика
    stats = {
        'pending_reports': Report.objects.filter(status='pending').count(),
        'pending_queue': ModerationQueue.objects.filter(status='pending').count(),
        'active_bans': UserBan.objects.filter(is_active=True).count(),
        'automod_today': AutoModeration.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
    }
    
    # Последние действия
    recent_reports = Report.objects.select_related(
        'reporter', 'listing', 'reported_user'
    ).order_by('-created_at')[:10]
    
    recent_automod = AutoModeration.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_reports': recent_reports,
        'recent_automod': recent_automod,
    }
    return render(request, 'core/moderation_dashboard.html', context)


@login_required
def my_reports(request):
    """Мои жалобы"""
    reports = Report.objects.filter(
        reporter=request.user
    ).select_related('listing', 'reported_user').order_by('-created_at')
    
    context = {
        'reports': reports
    }
    return render(request, 'core/my_reports.html', context)


@login_required
@user_passes_test(is_moderator)
def reports_queue(request):
    """Очередь жалоб для модераторов"""
    status = request.GET.get('status', 'pending')
    
    reports = Report.objects.select_related(
        'reporter', 'listing', 'reported_user'
    ).filter(status=status).order_by('-created_at')
    
    context = {
        'reports': reports,
        'current_status': status,
    }
    return render(request, 'core/reports_queue.html', context)


@login_required
@user_passes_test(is_moderator)
def process_report(request, report_id):
    """Обработка жалобы"""
    report = get_object_or_404(Report, id=report_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_comment = request.POST.get('admin_comment', '')
        
        if action == 'approve':
            report.status = 'resolved'
            report.admin_comment = admin_comment
            report.resolved_at = timezone.now()
            report.save()
            
            messages.success(request, 'Жалоба одобрена и обработана')
        
        elif action == 'reject':
            report.status = 'rejected'
            report.admin_comment = admin_comment
            report.resolved_at = timezone.now()
            report.save()
            
            messages.success(request, 'Жалоба отклонена')
        
        elif action == 'ban_user':
            # Создаем бан
            ban_days = int(request.POST.get('ban_days', 7))
            reported_user = report.reported_user if report.report_type == 'user' else report.listing.seller
            
            UserBan.objects.create(
                user=reported_user,
                ban_type='temporary' if ban_days > 0 else 'permanent',
                reason=report.reason,
                description=report.description,
                moderator=request.user,
                expires_at=timezone.now() + timezone.timedelta(days=ban_days) if ban_days > 0 else None
            )
            
            report.status = 'resolved'
            report.admin_comment = f'Пользователь забанен на {ban_days} дней'
            report.resolved_at = timezone.now()
            report.save()
            
            messages.success(request, f'Пользователь забанен на {ban_days} дней')
        
        return redirect('core:reports_queue')
    
    context = {
        'report': report
    }
    return render(request, 'core/process_report.html', context)


@login_required
@user_passes_test(is_moderator)
def user_bans_list(request):
    """Список банов"""
    active_only = request.GET.get('active', 'true') == 'true'
    
    bans = UserBan.objects.select_related('user', 'moderator').all()
    
    if active_only:
        bans = bans.filter(is_active=True)
    
    bans = bans.order_by('-created_at')
    
    context = {
        'bans': bans,
        'active_only': active_only
    }
    return render(request, 'core/user_bans_list.html', context)

