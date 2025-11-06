"""
Автоматическая модерация контента.
"""
import re
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AutoModerator:
    """
    Автоматический модератор для фильтрации нежелательного контента.
    """
    
    # Паттерны для обнаружения
    PROFANITY_PATTERNS = [
        r'\b(хуй|пизд|ебл|бля|сук|муда|пидор|гандон)\w*',
        r'\b(fuck|shit|bitch|ass)\w*',
    ]
    
    SPAM_PATTERNS = [
        r'(купи|продам|заработок|доход)\s+(здесь|тут|сейчас)',
        r'(telegram|whatsapp|viber)\s*[@:]\s*[\w\d]+',
        r'https?://(bit\.ly|goo\.gl|tinyurl|vk\.cc)',  # Короткие ссылки
        r'(\d{10,})',  # Длинные номера телефонов
    ]
    
    SCAM_PATTERNS = [
        r'(гарант|гарантия)\s+(100%|обязательно)',
        r'(обман|мошенник|кидала)\s+(не|нет)',
        r'предоплата\s+обязательна',
        r'(яндекс|киви|карта)\s+\d{10,}',  # Реквизиты для оплаты
    ]
    
    def __init__(self):
        self.profanity_regex = re.compile('|'.join(self.PROFANITY_PATTERNS), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.SPAM_PATTERNS), re.IGNORECASE)
        self.scam_regex = re.compile('|'.join(self.SCAM_PATTERNS), re.IGNORECASE)
    
    def check_text(self, text):
        """
        Проверить текст на нежелательный контент.
        
        Returns:
            dict: {
                'is_clean': bool,
                'violations': list,
                'severity': 'low'|'medium'|'high'
            }
        """
        violations = []
        severity = 'low'
        
        # Проверка на мат
        if self.profanity_regex.search(text):
            violations.append({
                'type': 'profanity',
                'message': 'Обнаружена нецензурная лексика'
            })
            severity = 'medium'
        
        # Проверка на спам
        spam_matches = self.spam_regex.findall(text)
        if spam_matches:
            violations.append({
                'type': 'spam',
                'message': 'Обнаружены признаки спама',
                'matches': spam_matches[:3]  # Первые 3 совпадения
            })
            severity = 'medium' if severity == 'low' else 'high'
        
        # Проверка на мошенничество
        scam_matches = self.scam_regex.findall(text)
        if scam_matches:
            violations.append({
                'type': 'scam',
                'message': 'Обнаружены признаки мошенничества'
            })
            severity = 'high'
        
        return {
            'is_clean': len(violations) == 0,
            'violations': violations,
            'severity': severity
        }
    
    def moderate_listing(self, listing):
        """Проверить объявление"""
        text = f"{listing.title} {listing.description}"
        result = self.check_text(text)
        
        if not result['is_clean']:
            self._log_violation(
                content_type='listing',
                content_id=listing.id,
                user=listing.seller,
                violations=result['violations'],
                severity=result['severity']
            )
            
            if result['severity'] == 'high':
                # Автоматически скрываем
                listing.status = 'cancelled'
                listing.save()
                return 'blocked'
            elif result['severity'] == 'medium':
                # Добавляем в очередь модерации
                from .moderation_models import ModerationQueue
                ModerationQueue.objects.get_or_create(
                    content_type='listing',
                    content_id=listing.id,
                    user=listing.seller,
                    defaults={'priority': 5}
                )
                return 'flagged'
        
        return 'approved'
    
    def moderate_message(self, message):
        """Проверить сообщение"""
        result = self.check_text(message.content)
        
        if not result['is_clean']:
            self._log_violation(
                content_type='message',
                content_id=message.id,
                user=message.sender,
                violations=result['violations'],
                severity=result['severity']
            )
            
            if result['severity'] == 'high':
                return 'blocked'
            else:
                return 'warned'
        
        return 'approved'
    
    def _log_violation(self, content_type, content_id, user, violations, severity):
        """Логирование нарушения"""
        from .moderation_models import AutoModeration
        
        action = {
            'low': 'flag',
            'medium': 'warn',
            'high': 'block'
        }.get(severity, 'flag')
        
        AutoModeration.objects.create(
            content_type=content_type,
            content_id=content_id,
            user=user,
            action=action,
            reason=f"Обнаружено нарушений: {len(violations)}",
            matched_patterns=[v['type'] for v in violations]
        )
        
        logger.warning(f'AutoMod {action}: {content_type} #{content_id} by {user.username}')


# Singleton
auto_moderator = AutoModerator()

