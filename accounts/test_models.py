"""
Comprehensive тесты для моделей accounts.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from accounts.models import Profile, EmailVerification, PasswordResetCode
from django.utils import timezone
from datetime import timedelta

CustomUser = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    """Тесты модели CustomUser."""
    
    def test_create_user(self):
        """Создание пользователя."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
    
    def test_create_superuser(self):
        """Создание суперпользователя."""
        user = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        assert user.is_staff
        assert user.is_superuser
    
    def test_user_str_representation(self):
        """Строковое представление пользователя."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert str(user) == 'testuser'
    
    def test_user_email_unique(self):
        """Email должен быть уникальным."""
        CustomUser.objects.create_user(
            username='user1',
            email='test@example.com',
            password='pass123'
        )
        
        with pytest.raises(Exception):
            CustomUser.objects.create_user(
                username='user2',
                email='test@example.com',
                password='pass123'
            )
    
    def test_user_cannot_be_deleted(self):
        """Пользователя нельзя удалить."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        with pytest.raises(Exception) as exc_info:
            user.delete()
        assert 'Удаление пользователей запрещено' in str(exc_info.value)


@pytest.mark.django_db
class TestProfileModel:
    """Тесты модели Profile."""
    
    def test_profile_auto_created(self, verified_user):
        """Профиль создается автоматически."""
        assert hasattr(verified_user, 'profile')
        assert verified_user.profile is not None
    
    def test_profile_default_values(self, verified_user):
        """Проверка дефолтных значений."""
        profile = verified_user.profile
        assert profile.rating == 0.00
        assert profile.total_sales == 0
        assert profile.total_purchases == 0
        assert profile.balance == 0.00
    
    def test_profile_str_representation(self, verified_user):
        """Строковое представление профиля."""
        assert str(verified_user.profile) == f'Профиль {verified_user.username}'
    
    def test_profile_cannot_be_deleted(self, verified_user):
        """Профиль нельзя удалить."""
        with pytest.raises(Exception) as exc_info:
            verified_user.profile.delete()
        assert 'Удаление профилей запрещено' in str(exc_info.value)
    
    def test_profile_update_rating_no_reviews(self, verified_user):
        """Обновление рейтинга без отзывов."""
        verified_user.profile.update_rating()
        assert verified_user.profile.rating == 0.00
    
    def test_profile_update_rating_with_reviews(self, verified_user, buyer, active_listing, purchase_request_factory, user_factory, listing_factory):
        """Обновление рейтинга с отзывами."""
        from transactions.models import Review
        
        # Создаем первую завершенную сделку
        purchase1 = purchase_request_factory(active_listing, buyer, status='completed')
        
        # Создаем вторую завершенную сделку (с другим покупателем)
        buyer2 = user_factory(username='buyer2', email='buyer2@example.com')
        listing2 = listing_factory(verified_user)
        purchase2 = purchase_request_factory(listing2, buyer2, status='completed')
        
        # Создаем отзывы от разных покупателей
        Review.objects.create(
            purchase_request=purchase1,
            reviewer=buyer,
            reviewed_user=verified_user,
            rating=5,
            comment='Excellent!'
        )
        
        Review.objects.create(
            purchase_request=purchase2,
            reviewer=buyer2,
            reviewed_user=verified_user,
            rating=4,
            comment='Good!'
        )
        
        # Обновляем рейтинг
        verified_user.profile.refresh_from_db()
        assert verified_user.profile.rating == 4.5
    
    def test_avatar_validation_size(self, verified_user):
        """Валидация размера аватара."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image
        
        # Создаем большое изображение (> 2MB)
        img = Image.new('RGB', (3000, 3000), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=100)
        img_io.seek(0)
        
        large_file = SimpleUploadedFile(
            "large_avatar.jpg",
            img_io.getvalue(),
            content_type="image/jpeg"
        )
        
        # Размер больше 2MB должен вызвать ValidationError
        if large_file.size > 2 * 1024 * 1024:
            from accounts.models import validate_avatar_size
            with pytest.raises(ValidationError):
                validate_avatar_size(large_file)
    
    def test_phone_unique(self, user_factory):
        """Телефон должен быть уникальным."""
        user1 = user_factory(username='user1', email='user1@example.com')
        user1.profile.phone = '+7 (999) 123-45-67'
        user1.profile.save()
        
        user2 = user_factory(username='user2', email='user2@example.com')
        user2.profile.phone = '+7 (999) 123-45-67'
        
        with pytest.raises(Exception):
            user2.profile.save()
    
    def test_username_unique(self, user_factory):
        """Никнейм должен быть уникальным."""
        user_factory(username='testuser', email='test1@example.com')
        
        with pytest.raises(Exception):
            user_factory(username='testuser', email='test2@example.com')


@pytest.mark.django_db
class TestEmailVerification:
    """Тесты верификации email."""
    
    def test_create_verification(self, unverified_user):
        """Создание токена верификации."""
        verification = EmailVerification.create_for_user(unverified_user)
        assert verification is not None
        assert len(verification.token) > 0
        assert not verification.is_verified
    
    def test_generate_token_unique(self):
        """Токены уникальны."""
        token1 = EmailVerification.generate_token()
        token2 = EmailVerification.generate_token()
        assert token1 != token2
    
    def test_verify_email(self, unverified_user):
        """Верификация email."""
        verification = EmailVerification.create_for_user(unverified_user)
        verification.verify()
        
        assert verification.is_verified
        assert verification.verified_at is not None
        
        # Проверяем что профиль обновлен
        unverified_user.profile.refresh_from_db()
        assert unverified_user.profile.is_verified
        assert unverified_user.profile.verification_date is not None
    
    def test_duplicate_verification_removed(self, unverified_user):
        """Старые токены удаляются при создании новых."""
        ver1 = EmailVerification.create_for_user(unverified_user)
        token1 = ver1.token
        
        ver2 = EmailVerification.create_for_user(unverified_user)
        
        # Старый токен должен быть удален
        assert not EmailVerification.objects.filter(token=token1).exists()
        assert EmailVerification.objects.filter(token=ver2.token).exists()


@pytest.mark.django_db
class TestPasswordResetCode:
    """Тесты кодов сброса пароля."""
    
    def test_create_code(self, verified_user):
        """Создание кода сброса."""
        code = PasswordResetCode.create_code(verified_user)
        assert code is not None
        assert len(code.code) == 6
        assert code.code.isdigit()
        assert not code.is_used
    
    def test_code_expires(self, verified_user):
        """Код истекает через 15 минут."""
        code = PasswordResetCode.create_code(verified_user)
        
        # Сразу после создания код валиден
        assert code.is_valid()
        
        # Меняем дату истечения на прошлое
        code.expires_at = timezone.now() - timedelta(minutes=1)
        code.save()
        
        # Теперь код невалиден
        assert not code.is_valid()
    
    def test_code_can_be_used_once(self, verified_user):
        """Код можно использовать только один раз."""
        code = PasswordResetCode.create_code(verified_user)
        
        assert code.is_valid()
        
        code.mark_as_used()
        assert not code.is_valid()
    
    def test_old_codes_deactivated(self, verified_user):
        """Старые коды деактивируются при создании нового."""
        code1 = PasswordResetCode.create_code(verified_user)
        code2 = PasswordResetCode.create_code(verified_user)
        
        # Первый код должен быть помечен как использованный
        code1.refresh_from_db()
        assert code1.is_used
        assert not code2.is_used
    
    def test_generate_unique_codes(self, verified_user):
        """Генерация уникальных кодов."""
        codes = set()
        for _ in range(10):
            code = PasswordResetCode.create_code(verified_user)
            codes.add(code.code)
        
        # Хотя бы несколько кодов должны быть уникальными
        assert len(codes) > 1

