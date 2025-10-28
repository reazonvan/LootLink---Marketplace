"""
Тесты для приложения accounts.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import Profile, EmailVerification

CustomUser = get_user_model()


class UserRegistrationTest(TestCase):
    """Тесты регистрации пользователя."""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
    
    def test_registration_page_loads(self):
        """Страница регистрации загружается."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Регистрация')
    
    def test_user_registration_creates_profile(self):
        """При регистрации автоматически создается профиль."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'testpass123!@#',
            'password2': 'testpass123!@#',
        }
        response = self.client.post(self.register_url, data)
        
        # Проверяем что пользователь создан
        user = CustomUser.objects.get(username='testuser')
        self.assertIsNotNone(user)
        
        # Проверяем что профиль создан автоматически
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.phone, '+7 (999) 123-45-67')
    
    def test_duplicate_email_rejected(self):
        """Нельзя зарегистрировать пользователя с существующим email."""
        # Создаем первого пользователя
        CustomUser.objects.create_user(
            username='user1',
            email='test@example.com',
            password='pass123'
        )
        
        # Пытаемся создать второго с тем же email
        data = {
            'username': 'user2',
            'email': 'test@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'testpass123!@#',
            'password2': 'testpass123!@#',
        }
        response = self.client.post(self.register_url, data)
        
        # Проверяем что регистрация не прошла
        self.assertEqual(CustomUser.objects.filter(username='user2').count(), 0)


class ProfileModelTest(TestCase):
    """Тесты модели Profile."""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_profile_created_automatically(self):
        """Профиль создается автоматически при создании пользователя."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
    
    def test_profile_default_values(self):
        """Проверка дефолтных значений профиля."""
        profile = self.user.profile
        self.assertEqual(profile.rating, 0.00)
        self.assertEqual(profile.total_sales, 0)
        self.assertEqual(profile.total_purchases, 0)
        self.assertFalse(profile.is_verified)
        self.assertEqual(profile.balance, 0.00)
    
    def test_profile_cannot_be_deleted(self):
        """Профиль нельзя удалить."""
        profile = self.user.profile
        with self.assertRaises(Exception):
            profile.delete()
    
    def test_update_rating(self):
        """Обновление рейтинга работает."""
        profile = self.user.profile
        profile.update_rating()
        # После обновления без отзывов рейтинг должен быть 0
        self.assertEqual(profile.rating, 0.00)


class UserLoginTest(TestCase):
    """Тесты входа пользователя."""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('accounts:login')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_page_loads(self):
        """Страница входа загружается."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Вход')
    
    def test_successful_login(self):
        """Успешный вход."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123',
        })
        # После успешного входа должен быть редирект
        self.assertEqual(response.status_code, 302)
    
    def test_invalid_credentials(self):
        """Вход с неверными данными."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        # Должны остаться на странице входа
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Вход')


class EmailVerificationTest(TestCase):
    """Тесты верификации email."""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_verification_token(self):
        """Создание токена верификации."""
        verification = EmailVerification.create_for_user(self.user)
        self.assertIsNotNone(verification)
        self.assertIsNotNone(verification.token)
        self.assertFalse(verification.is_verified)
    
    def test_verify_email(self):
        """Верификация email."""
        verification = EmailVerification.create_for_user(self.user)
        verification.verify()
        
        # Проверяем что email верифицирован
        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)
        self.assertIsNotNone(verification.verified_at)
        
        # Проверяем что профиль обновлен
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)
