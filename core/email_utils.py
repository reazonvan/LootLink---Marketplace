"""
Email утилиты для отправки уведомлений.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_purchase_request_notification(purchase_request):
    """Уведомление продавцу о новом запросе на покупку."""
    subject = f'Новый запрос на покупку: {purchase_request.listing.title}'
    
    context = {
        'purchase_request': purchase_request,
        'listing': purchase_request.listing,
        'buyer': purchase_request.buyer,
    }
    
    message = render_to_string('emails/purchase_request_notification.txt', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[purchase_request.seller.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def send_purchase_request_accepted_notification(purchase_request):
    """Уведомление покупателю о принятии запроса."""
    subject = f'Ваш запрос принят: {purchase_request.listing.title}'
    
    context = {
        'purchase_request': purchase_request,
        'listing': purchase_request.listing,
        'seller': purchase_request.seller,
    }
    
    message = render_to_string('emails/purchase_request_accepted.txt', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[purchase_request.buyer.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def send_new_message_notification(message_obj, recipient):
    """Уведомление о новом сообщении."""
    subject = f'Новое сообщение от {message_obj.sender.username}'
    
    context = {
        'message': message_obj,
        'sender': message_obj.sender,
        'conversation': message_obj.conversation,
    }
    
    message = render_to_string('emails/new_message_notification.txt', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def send_review_notification(review):
    """Уведомление о новом отзыве."""
    subject = f'Вы получили новый отзыв от {review.reviewer.username}'
    
    context = {
        'review': review,
        'reviewer': review.reviewer,
    }
    
    message = render_to_string('emails/review_notification.txt', context)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[review.reviewed_user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def create_notification(user, notification_type, title, message, link=''):
    """
    Создает уведомление в БД для пользователя.
    
    Args:
        user: CustomUser - пользователь
        notification_type: str - тип уведомления (см. Notification.NOTIFICATION_TYPES)
        title: str - заголовок
        message: str - текст сообщения  
        link: str - ссылка для перехода (опционально)
    
    Returns:
        Notification - созданное уведомление
    """
    from core.models import Notification
    
    return Notification.create_notification(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )