"""
Comprehensive тесты для форм приложения accounts.
"""
import pytest
from accounts.forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ProfileUpdateForm,
    UserUpdateForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm
)
from django.contrib.auth import get_user_model
from accounts.models import Profile, PasswordResetCode

CustomUser = get_user_model()


@pytest.mark.django_db
class TestCustomUserCreationForm:
    """Тесты формы регистрации."""
    
    def test_valid_form(self):
        """Валидная форма."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'complexP@ss123',
            'password2': 'complexP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert form.is_valid()
    
    def test_duplicate_email(self, verified_user):
        """Дубликат email."""
        data = {
            'username': 'anotheruser',
            'email': verified_user.email,
            'phone': '+7 (999) 123-45-68',
            'password1': 'complexP@ss123',
            'password2': 'complexP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors
    
    def test_duplicate_phone(self, verified_user):
        """Дубликат телефона."""
        verified_user.profile.phone = '+7 (999) 123-45-67'
        verified_user.profile.save()
        
        data = {
            'username': 'anotheruser',
            'email': 'another@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'complexP@ss123',
            'password2': 'complexP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert not form.is_valid()
        assert 'phone' in form.errors
    
    def test_invalid_phone_format(self):
        """Невалидный формат телефона."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '123',  # Слишком короткий
            'password1': 'complexP@ss123',
            'password2': 'complexP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert not form.is_valid()
        assert 'phone' in form.errors
    
    def test_password_mismatch(self):
        """Пароли не совпадают."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'complexP@ss123',
            'password2': 'differentP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert not form.is_valid()
    
    def test_form_save_creates_profile(self):
        """Сохранение формы создает профиль."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '+7 (999) 123-45-67',
            'password1': 'complexP@ss123',
            'password2': 'complexP@ss123',
        }
        form = CustomUserCreationForm(data=data)
        assert form.is_valid()
        
        user = form.save()
        assert user.profile.phone == '+7 (999) 123-45-67'


@pytest.mark.django_db
class TestProfileUpdateForm:
    """Тесты формы обновления профиля."""
    
    def test_valid_form(self, verified_user):
        """Валидная форма."""
        data = {
            'bio': 'New bio',
            'telegram': '@telegram',
            'discord': 'discord#1234',
        }
        form = ProfileUpdateForm(data=data, instance=verified_user.profile)
        assert form.is_valid()
    
    def test_phone_readonly_when_set(self, verified_user):
        """Телефон readonly когда уже установлен."""
        verified_user.profile.phone = '+7 (999) 123-45-67'
        verified_user.profile.save()
        
        form = ProfileUpdateForm(instance=verified_user.profile)
        assert form.fields['phone'].disabled
    
    def test_phone_editable_when_empty(self, verified_user):
        """Телефон можно установить если еще не установлен."""
        verified_user.profile.phone = None
        verified_user.profile.save()
        
        form = ProfileUpdateForm(instance=verified_user.profile)
        assert not form.fields['phone'].disabled


@pytest.mark.django_db
class TestUserUpdateForm:
    """Тесты формы обновления пользователя."""
    
    def test_username_readonly(self, verified_user):
        """Username нельзя изменить."""
        form = UserUpdateForm(instance=verified_user)
        assert form.fields['username'].disabled
    
    def test_email_readonly(self, verified_user):
        """Email нельзя изменить."""
        form = UserUpdateForm(instance=verified_user)
        assert form.fields['email'].disabled


@pytest.mark.django_db
class TestPasswordResetRequestForm:
    """Тесты формы запроса сброса пароля."""
    
    def test_valid_email(self, verified_user):
        """Валидный email."""
        data = {'email': verified_user.email}
        form = PasswordResetRequestForm(data=data)
        assert form.is_valid()
    
    def test_invalid_email(self):
        """Несуществующий email."""
        data = {'email': 'nonexistent@example.com'}
        form = PasswordResetRequestForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors


@pytest.mark.django_db
class TestPasswordResetConfirmForm:
    """Тесты формы подтверждения сброса пароля."""
    
    def test_valid_code(self, verified_user):
        """Валидный код."""
        reset_code = PasswordResetCode.create_code(verified_user)
        
        data = {
            'code': reset_code.code,
            'new_password1': 'newP@ss123',
            'new_password2': 'newP@ss123',
        }
        form = PasswordResetConfirmForm(data=data, user=verified_user)
        assert form.is_valid()
    
    def test_invalid_code(self, verified_user):
        """Невалидный код."""
        data = {
            'code': '000000',
            'new_password1': 'newP@ss123',
            'new_password2': 'newP@ss123',
        }
        form = PasswordResetConfirmForm(data=data, user=verified_user)
        assert not form.is_valid()
        assert 'code' in form.errors
    
    def test_password_mismatch(self, verified_user):
        """Пароли не совпадают."""
        reset_code = PasswordResetCode.create_code(verified_user)
        
        data = {
            'code': reset_code.code,
            'new_password1': 'newP@ss123',
            'new_password2': 'differentP@ss123',
        }
        form = PasswordResetConfirmForm(data=data, user=verified_user)
        assert not form.is_valid()
    
    def test_save_changes_password(self, verified_user):
        """Сохранение меняет пароль."""
        reset_code = PasswordResetCode.create_code(verified_user)
        old_password = verified_user.password
        
        data = {
            'code': reset_code.code,
            'new_password1': 'newP@ss123',
            'new_password2': 'newP@ss123',
        }
        form = PasswordResetConfirmForm(data=data, user=verified_user)
        assert form.is_valid()
        
        form.save()
        
        verified_user.refresh_from_db()
        assert verified_user.password != old_password
        assert verified_user.check_password('newP@ss123')
        
        # Код должен быть помечен как использованный
        reset_code.refresh_from_db()
        assert reset_code.is_used

