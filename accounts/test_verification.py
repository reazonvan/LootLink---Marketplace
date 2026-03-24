"""
Тесты для системы верификации (Email, SMS, Документы).
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from accounts.models import CustomUser, Profile, EmailVerification, PhoneVerification, DocumentVerification
import io
from PIL import Image


class EmailVerificationTestCase(TestCase):
    """Тесты email верификации"""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_email_verification_created_on_registration(self):
        """Email верификация создается при регистрации"""
        verification = EmailVerification.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification)
        self.assertFalse(verification.is_verified)
        self.assertIsNotNone(verification.token)

    def test_verify_email_with_valid_token(self):
        """Верификация email с валидным токеном"""
        verification = EmailVerification.create_for_user(self.user)

        response = self.client.get(
            reverse('accounts:verify_email', kwargs={'token': verification.token})
        )

        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)
        self.assertIsNotNone(verification.verified_at)

    def test_verify_email_with_invalid_token(self):
        """Верификация email с невалидным токеном"""
        response = self.client.get(
            reverse('accounts:verify_email', kwargs={'token': 'invalid-token-123'})
        )

        self.assertEqual(response.status_code, 302)  # Redirect

    def test_resend_verification_email(self):
        """Повторная отправка письма верификации"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(reverse('accounts:resend_verification_email'))

        self.assertEqual(response.status_code, 302)  # Redirect


class PhoneVerificationTestCase(TestCase):
    """Тесты SMS верификации"""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profile.phone = '+79991234567'
        self.user.profile.save()

    def test_create_phone_verification(self):
        """Создание SMS верификации"""
        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        self.assertIsNotNone(verification)
        self.assertEqual(len(verification.code), 6)
        self.assertFalse(verification.is_verified)
        self.assertEqual(verification.attempts, 0)

    def test_verify_with_correct_code(self):
        """Верификация с правильным кодом"""
        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        success, message = verification.verify(verification.code)

        self.assertTrue(success)
        self.assertTrue(verification.is_verified)
        self.assertIsNotNone(verification.verified_at)

        # Проверяем что профиль обновился
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)

    def test_verify_with_incorrect_code(self):
        """Верификация с неправильным кодом"""
        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        success, message = verification.verify('000000')

        self.assertFalse(success)
        self.assertFalse(verification.is_verified)
        self.assertEqual(verification.attempts, 1)

    def test_verify_max_attempts_exceeded(self):
        """Превышение максимального количества попыток"""
        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        # 5 неудачных попыток
        for i in range(5):
            success, message = verification.verify('000000')
            self.assertFalse(success)

        # 6-я попытка должна быть отклонена
        success, message = verification.verify(verification.code)
        self.assertFalse(success)
        self.assertIn('Превышено количество попыток', message)

    def test_verify_expired_code(self):
        """Верификация истекшего кода"""
        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        # Делаем код истекшим
        verification.expires_at = timezone.now() - timedelta(minutes=1)
        verification.save()

        success, message = verification.verify(verification.code)

        self.assertFalse(success)
        self.assertIn('истек', message.lower())

    def test_phone_verification_request_view(self):
        """Тест view запроса SMS кода"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(reverse('accounts:phone_verification_request'))

        # Проверяем что верификация создана
        verification = PhoneVerification.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification)

    def test_phone_verification_confirm_view(self):
        """Тест view подтверждения SMS кода"""
        self.client.login(username='testuser', password='testpass123')

        verification = PhoneVerification.create_for_user(self.user, self.user.profile.phone)

        response = self.client.post(
            reverse('accounts:phone_verification_confirm'),
            {'code': verification.code}
        )

        verification.refresh_from_db()
        self.assertTrue(verification.is_verified)


class DocumentVerificationTestCase(TestCase):
    """Тесты верификации документов"""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

    def create_test_image(self):
        """Создает тестовое изображение"""
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(file, 'jpeg')
        file.seek(0)
        return SimpleUploadedFile('test.jpg', file.read(), content_type='image/jpeg')

    def test_create_document_verification(self):
        """Создание верификации документа"""
        doc = DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=self.create_test_image()
        )

        self.assertEqual(doc.status, 'pending')
        self.assertIsNone(doc.reviewed_by)
        self.assertIsNone(doc.reviewed_at)

    def test_approve_document(self):
        """Одобрение документа"""
        doc = DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=self.create_test_image()
        )

        doc.approve(self.admin, 'Документ одобрен')

        self.assertEqual(doc.status, 'approved')
        self.assertEqual(doc.reviewed_by, self.admin)
        self.assertIsNotNone(doc.reviewed_at)
        self.assertEqual(doc.admin_comment, 'Документ одобрен')

    def test_reject_document(self):
        """Отклонение документа"""
        doc = DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=self.create_test_image()
        )

        doc.reject(self.admin, 'Документ нечитаемый')

        self.assertEqual(doc.status, 'rejected')
        self.assertEqual(doc.reviewed_by, self.admin)
        self.assertIsNotNone(doc.reviewed_at)

    def test_user_verified_after_all_documents_approved(self):
        """Пользователь верифицируется после одобрения всех документов"""
        # Создаем паспорт
        passport = DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=self.create_test_image()
        )
        passport.approve(self.admin)

        # Пользователь еще не верифицирован (нужно селфи)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_verified)

        # Создаем селфи
        selfie = DocumentVerification.objects.create(
            user=self.user,
            document_type='selfie',
            document_file=self.create_test_image()
        )
        selfie.approve(self.admin)

        # Теперь пользователь верифицирован
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)
        self.assertIsNotNone(self.user.profile.verification_date)

    def test_document_upload_view(self):
        """Тест view загрузки документа"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(
            reverse('accounts:document_verification_upload'),
            {
                'document_type': 'passport',
                'document_file': self.create_test_image()
            }
        )

        # Проверяем что документ создан
        doc = DocumentVerification.objects.filter(user=self.user).first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.document_type, 'passport')

    def test_document_status_view(self):
        """Тест view статуса документов"""
        self.client.login(username='testuser', password='testpass123')

        # Создаем документ
        DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=self.create_test_image()
        )

        response = self.client.get(reverse('accounts:document_verification_status'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Паспорт')


class VerificationIntegrationTestCase(TestCase):
    """Интеграционные тесты полного процесса верификации"""

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profile.phone = '+79991234567'
        self.user.profile.save()

    def test_full_verification_flow(self):
        """Полный процесс верификации: Email -> SMS -> Документы"""
        # 1. Email верификация
        email_verification = EmailVerification.create_for_user(self.user)
        email_verification.verify()

        # 2. SMS верификация
        phone_verification = PhoneVerification.create_for_user(
            self.user,
            self.user.profile.phone
        )
        success, _ = phone_verification.verify(phone_verification.code)
        self.assertTrue(success)

        # 3. Документы (паспорт + селфи)
        admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

        # Создаем тестовое изображение
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(file, 'jpeg')
        file.seek(0)
        test_image = SimpleUploadedFile('test.jpg', file.read(), content_type='image/jpeg')

        passport = DocumentVerification.objects.create(
            user=self.user,
            document_type='passport',
            document_file=test_image
        )
        passport.approve(admin)

        # Создаем второе изображение для селфи
        file2 = io.BytesIO()
        image2 = Image.new('RGB', (100, 100), color='blue')
        image2.save(file2, 'jpeg')
        file2.seek(0)
        test_image2 = SimpleUploadedFile('test2.jpg', file2.read(), content_type='image/jpeg')

        selfie = DocumentVerification.objects.create(
            user=self.user,
            document_type='selfie',
            document_file=test_image2
        )
        selfie.approve(admin)

        # Проверяем финальный статус
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_verified)

        # Проверяем что все верификации пройдены
        self.assertTrue(email_verification.is_verified)
        self.assertTrue(phone_verification.is_verified)
        self.assertEqual(
            DocumentVerification.objects.filter(
                user=self.user,
                status='approved'
            ).count(),
            2
        )
