"""
Сервисные классы для бизнес-логики приложения.
Централизованное управление уведомлениями и email.
"""
from typing import Optional
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import escape
from .models import Notification


class NotificationService:
    """
    Сервис для создания и отправки уведомлений.
    Централизует всю логику уведомлений в одном месте.
    """
    
    @staticmethod
    def create_and_notify(
        user,
        notification_type: str,
        title: str,
        message: str,
        link: str = '',
        send_email: bool = True,
        email_template: Optional[str] = None
    ) -> Notification:
        """
        Создает уведомление в БД и опционально отправляет email.
        
        Args:
            user: Пользователь-получатель
            notification_type: Тип уведомления (из Notification.NOTIFICATION_TYPES)
            title: Заголовок уведомления
            message: Текст сообщения
            link: Ссылка для перехода (опционально)
            send_email: Отправлять ли email (по умолчанию True)
            email_template: Шаблон для email (опционально)
        
        Returns:
            Созданное уведомление
        """
        # Создаем уведомление в БД
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
        
        # Отправляем email асинхронно через Celery если требуется
        if send_email and user.email:
            try:
                # Используем Celery для асинхронной отправки
                from core.tasks import send_email_async
                
                # Формируем email
                email_subject = f'{title} - LootLink'
                email_body = NotificationService._format_email_body(user, message, link)
                
                # Отправляем асинхронно
                send_email_async.delay(email_subject, email_body, user.email)
            except Exception as e:
                # Fallback на синхронную отправку если Celery недоступен
                try:
                    NotificationService._send_notification_email(
                        user=user,
                        title=title,
                        message=message,
                        link=link
                    )
                except Exception as email_error:
                    # Логируем ошибку но не ломаем функциональность
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Ошибка отправки email уведомления: {email_error}')
        
        return notification
    
    @staticmethod
    def _format_email_body(user, message: str, link: str = '') -> str:
        """
        Форматирует тело email письма.
        
        Args:
            user: Пользователь-получатель
            message: Текст сообщения
            link: Ссылка (опционально)
        
        Returns:
            Отформатированное тело письма
        """
        # Экранируем контент для безопасности (защита от XSS)
        safe_message = escape(message)
        
        email_body = f"""
Здравствуйте, {user.username}!

{safe_message}
"""
        
        if link:
            # Создаем полный URL если это относительная ссылка
            if link.startswith('/'):
                domain = settings.SITE_URL.replace('http://', '').replace('https://', '')
                protocol = 'https' if not settings.DEBUG else 'http'
                full_link = f"{protocol}://{domain}{link}"
            else:
                full_link = link
            
            email_body += f"\nПерейдите по ссылке: {full_link}\n"
        
        email_body += """
С уважением,
Команда LootLink
"""
        return email_body
    
    @staticmethod
    def _send_notification_email(user, title: str, message: str, link: str = ''):
        """
        Внутренний метод для синхронной отправки email уведомления (fallback).
        
        Args:
            user: Пользователь-получатель
            title: Заголовок письма
            message: Текст сообщения
            link: Ссылка (опционально)
        """
        email_subject = f'{title} - LootLink'
        email_body = NotificationService._format_email_body(user, message, link)
        
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )
    
    @staticmethod
    def notify_purchase_request(purchase_request):
        """Уведомление продавцу о новом запросе на покупку."""
        return NotificationService.create_and_notify(
            user=purchase_request.seller,
            notification_type='purchase_request',
            title=f'Новый запрос на покупку: {purchase_request.listing.title}',
            message=f'{purchase_request.buyer.username} хочет купить ваш товар за {purchase_request.listing.price} ₽',
            link=f'/transactions/purchase-request/{purchase_request.pk}/',
            send_email=True
        )
    
    @staticmethod
    def notify_request_accepted(purchase_request):
        """Уведомление покупателю о принятии запроса."""
        return NotificationService.create_and_notify(
            user=purchase_request.buyer,
            notification_type='request_accepted',
            title=f'Ваш запрос принят: {purchase_request.listing.title}',
            message=f'Продавец {purchase_request.seller.username} принял ваш запрос. Свяжитесь для завершения сделки.',
            link=f'/transactions/purchase-request/{purchase_request.pk}/',
            send_email=True
        )
    
    @staticmethod
    def notify_request_rejected(purchase_request):
        """Уведомление покупателю об отклонении запроса."""
        return NotificationService.create_and_notify(
            user=purchase_request.buyer,
            notification_type='request_rejected',
            title=f'Запрос отклонен: {purchase_request.listing.title}',
            message=f'К сожалению, продавец {purchase_request.seller.username} отклонил ваш запрос.',
            link=f'/transactions/purchase-request/{purchase_request.pk}/',
            send_email=True
        )
    
    @staticmethod
    def notify_deal_completed(purchase_request):
        """Уведомление покупателю о завершении сделки."""
        return NotificationService.create_and_notify(
            user=purchase_request.buyer,
            notification_type='deal_completed',
            title=f'Сделка завершена: {purchase_request.listing.title}',
            message=f'Продавец {purchase_request.seller.username} подтвердил завершение сделки. Оставьте отзыв!',
            link=f'/transactions/review/{purchase_request.pk}/create/',
            send_email=True
        )
    
    @staticmethod
    def notify_new_review(review):
        """Уведомление о новом отзыве."""
        stars = '⭐' * review.rating
        return NotificationService.create_and_notify(
            user=review.reviewed_user,
            notification_type='new_review',
            title=f'Новый отзыв от {review.reviewer.username}',
            message=f'Вы получили отзыв {stars} ({review.rating}/5) от {review.reviewer.username}',
            link=f'/accounts/profile/{review.reviewed_user.username}/',
            send_email=True
        )
    
    @staticmethod
    def notify_new_message(message_obj, recipient):
        """Уведомление о новом сообщении в чате."""
        # Обрезаем длинное сообщение
        preview = message_obj.content[:100]
        if len(message_obj.content) > 100:
            preview += '...'
        
        return NotificationService.create_and_notify(
            user=recipient,
            notification_type='new_message',
            title=f'Новое сообщение от {message_obj.sender.username}',
            message=preview,
            link=f'/chat/conversation/{message_obj.conversation.pk}/',
            send_email=True
        )

