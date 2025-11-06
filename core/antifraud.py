"""
Антифрод система.
"""
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class AntiFraudSystem:
    """
    Система обнаружения мошенничества.
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'low': 30,
            'medium': 60,
            'high': 80,
            'critical': 95
        }
    
    def check_user(self, user):
        """
        Проверить пользователя на мошенничество.
        
        Returns:
            dict: {'risk_score': int, 'flags': list, 'action': str}
        """
        flags = []
        risk_score = 0
        
        # Проверка 1: Новый аккаунт
        if (timezone.now() - user.date_joined).days < 1:
            flags.append('Аккаунт младше 1 дня')
            risk_score += 15
        
        # Проверка 2: Нет верификации
        if not user.profile.is_verified:
            flags.append('Email/телефон не верифицированы')
            risk_score += 20
        
        # Проверка 3: Низкий рейтинг или много плохих отзывов
        if user.profile.rating < 2.0 and user.profile.total_sales > 5:
            flags.append('Низкий рейтинг при большом количестве продаж')
            risk_score += 40
        
        # Проверка 4: Множественные активные объявления за короткий срок
        recent_listings = user.listings.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_listings > 10:
            flags.append(f'Создано {recent_listings} объявлений за час')
            risk_score += 30
        
        # Проверка 5: Подозрительные цены
        from listings.models import Listing
        avg_price_market = Listing.objects.filter(
            game=user.listings.first().game if user.listings.exists() else None
        ).aggregate(avg=models.Avg('price'))['avg'] or 0
        
        if avg_price_market > 0:
            user_listings = user.listings.filter(status='active')
            for listing in user_listings:
                if listing.price < avg_price_market * 0.3:  # Цена на 70% ниже рынка
                    flags.append(f'Подозрительно низкая цена: {listing.title}')
                    risk_score += 25
        
        # Определяем действие
        if risk_score >= self.risk_thresholds['critical']:
            action = 'block'
        elif risk_score >= self.risk_thresholds['high']:
            action = 'review'
        elif risk_score >= self.risk_thresholds['medium']:
            action = 'flag'
        else:
            action = 'allow'
        
        return {
            'risk_score': min(risk_score, 100),
            'flags': flags,
            'action': action,
            'level': self.get_risk_level(risk_score)
        }
    
    def check_transaction(self, purchase_request):
        """Проверить транзакцию"""
        flags = []
        risk_score = 0
        
        # Проверка покупателя и продавца
        buyer_risk = self.check_user(purchase_request.buyer)
        seller_risk = self.check_user(purchase_request.seller)
        
        risk_score += buyer_risk['risk_score'] * 0.5
        risk_score += seller_risk['risk_score'] * 0.5
        
        if buyer_risk['flags']:
            flags.extend([f'Покупатель: {f}' for f in buyer_risk['flags']])
        
        if seller_risk['flags']:
            flags.extend([f'Продавец: {f}' for f in seller_risk['flags']])
        
        return {
            'risk_score': int(risk_score),
            'flags': flags,
            'action': self.get_action_for_score(risk_score)
        }
    
    def get_risk_level(self, score):
        """Определить уровень риска"""
        if score >= 80:
            return 'critical'
        elif score >= 60:
            return 'high'
        elif score >= 30:
            return 'medium'
        return 'low'
    
    def get_action_for_score(self, score):
        """Определить действие по оценке"""
        if score >= self.risk_thresholds['critical']:
            return 'block'
        elif score >= self.risk_thresholds['high']:
            return 'review'
        elif score >= self.risk_thresholds['medium']:
            return 'flag'
        return 'allow'
    
    def log_fraud_check(self, user, result):
        """Логирование проверки"""
        if result['risk_score'] > 50:
            logger.warning(
                f'Antifraud: User {user.username} - Risk: {result["risk_score"]} - '
                f'Flags: {", ".join(result["flags"])}'
            )


# Singleton
antifraud_system = AntiFraudSystem()

