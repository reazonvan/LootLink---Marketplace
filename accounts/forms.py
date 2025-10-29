from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Profile, PasswordResetCode


class CustomUserCreationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя'
        })
    )
    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        }),
        label='Телефон',
        help_text='Введите номер телефона. Он будет неизменным.'
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone', 'password1', 'password2')
    
    def clean_username(self):
        """Проверка уникальности username (case-insensitive)."""
        username = self.cleaned_data.get('username')
        # Case-insensitive проверка (argear = Argear = ARGEAR)
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует (регистр не учитывается).')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def clean_phone(self):
        """Валидация номера телефона с проверкой формата."""
        import re
        phone = self.cleaned_data.get('phone')
        
        if not phone:
            raise forms.ValidationError('Номер телефона обязателен для заполнения.')
        
        # Удаляем все символы кроме цифр для проверки
        phone_digits = re.sub(r'\D', '', phone)
        
        # Проверка длины (10-11 цифр для российских номеров)
        if len(phone_digits) < 10 or len(phone_digits) > 11:
            raise forms.ValidationError(
                'Некорректный номер телефона. Введите номер в формате: +7 (999) 123-45-67'
            )
        
        # Проверка что номер начинается с 7 или 8 (для России)
        if len(phone_digits) == 11 and phone_digits[0] not in ['7', '8']:
            raise forms.ValidationError(
                'Номер должен начинаться с 7 или 8'
            )
        
        # Проверка на уникальность
        if Profile.objects.filter(phone=phone).exists():
            raise forms.ValidationError('Пользователь с таким номером телефона уже существует.')
        
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # Обновляем профиль пользователя с номером телефона
            user.profile.phone = self.cleaned_data.get('phone')
            user.profile.save()
            
            # Создаем токен верификации email
            from .models import EmailVerification, PasswordResetCode
            verification = EmailVerification.create_for_user(user)
            
            # Создаем код для SMS верификации (6-значный)
            sms_code = PasswordResetCode.create_code(user)
            
            # Отправляем письмо с подтверждением
            from django.core.mail import send_mail
            from django.conf import settings
            from django.urls import reverse
            
            # Формируем ссылку верификации
            domain = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
            protocol = 'https' if not settings.DEBUG else 'http'
            verification_url = f"{protocol}://{domain}{reverse('accounts:verify_email', kwargs={'token': verification.token})}"
            
            subject = 'Подтвердите ваш email - LootLink'
            email_message = f"""
Здравствуйте, {user.username}!

Спасибо за регистрацию на LootLink!

Для завершения регистрации подтвердите ваш email адрес, перейдя по ссылке:

{verification_url}

Или введите код подтверждения: {sms_code.code}

Ссылка и код действительны в течение 24 часов.

Если вы не регистрировались на LootLink, проигнорируйте это письмо.

С уважением,
Команда LootLink
"""
            
            # Отправляем email
            try:
                send_mail(
                    subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
            except Exception as e:
                # Логируем ошибку но не ломаем регистрацию
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка отправки email верификации: {e}')
            
            # Отправляем СМС с кодом подтверждения
            if user.profile.phone:
                try:
                    from core.sms_service import send_sms
                    sms_message = f'LootLink: Добро пожаловать, {user.username}! Ваш код подтверждения: {sms_code.code}'
                    send_sms(user.profile.phone, sms_message)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f'Ошибка отправки SMS: {e}')
        
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Форма входа в систему.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма редактирования профиля пользователя.
    ВАЖНО: Телефон можно указать только один раз!
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Если телефон уже указан - запрещаем его изменение
        if self.instance and self.instance.phone:
            self.fields['phone'].disabled = True
            self.fields['phone'].widget.attrs['readonly'] = 'readonly'
            self.fields['phone'].help_text = 'Телефон нельзя изменить после первого указания'
    
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'phone', 'telegram', 'discord']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Расскажите о себе...'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'telegram': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@username'
            }),
            'discord': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'username#1234'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }
        help_texts = {
            'phone': 'Телефон можно указать один раз. После этого его нельзя будет изменить.',
        }
    
    def clean_bio(self):
        """Валидация описания профиля."""
        bio = self.cleaned_data.get('bio')
        if bio and len(bio) > 500:
            raise forms.ValidationError('Описание не должно превышать 500 символов.')
        return bio
    
    def clean_telegram(self):
        """Валидация Telegram username."""
        telegram = self.cleaned_data.get('telegram')
        if telegram:
            telegram = telegram.strip()
            # Проверка формата @username
            if not telegram.startswith('@'):
                telegram = '@' + telegram
            # Проверка длины
            if len(telegram) < 6 or len(telegram) > 33:  # @username минимум 5 символов username
                raise forms.ValidationError('Telegram username должен быть от 5 до 32 символов (без @).')
            # Проверка только разрешенные символы
            import re
            if not re.match(r'^@[a-zA-Z0-9_]{5,32}$', telegram):
                raise forms.ValidationError('Telegram username может содержать только латинские буквы, цифры и подчеркивание.')
        return telegram
    
    def clean_discord(self):
        """Валидация Discord username."""
        discord = self.cleaned_data.get('discord')
        if discord:
            discord = discord.strip()
            # Проверка формата username#1234
            import re
            if not re.match(r'^.{2,32}#\d{4}$', discord):
                raise forms.ValidationError('Discord username должен быть в формате: username#1234')
        return discord


class UserUpdateForm(forms.ModelForm):
    """
    Форма обновления базовой информации пользователя.
    ВАЖНО: Эта форма больше не используется, так как username и email нельзя изменить,
    а ФИО мы не собираем согласно требованиям проекта.
    Оставлена для обратной совместимости.
    """
    username = forms.CharField(
        disabled=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text='Имя пользователя нельзя изменить'
    )
    email = forms.EmailField(
        disabled=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text='Email нельзя изменить'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email']


class PasswordResetRequestForm(forms.Form):
    """
    Форма запроса сброса пароля.
    Пользователь вводит email для получения кода.
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        }),
        help_text='На этот email будет отправлен код подтверждения'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email не найден.')
        return email


class PasswordResetConfirmForm(forms.Form):
    """
    Форма подтверждения сброса пароля с кодом.
    """
    code = forms.CharField(
        label='Код подтверждения',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123456',
            'maxlength': '6'
        }),
        help_text='Введите 6-значный код из письма'
    )
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Новый пароль'
        })
    )
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )
    
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not self.user:
            raise forms.ValidationError('Ошибка валидации.')
        
        try:
            reset_code = PasswordResetCode.objects.get(
                user=self.user,
                code=code,
                is_used=False
            )
            if not reset_code.is_valid():
                raise forms.ValidationError('Код истёк или уже использован.')
            self.reset_code = reset_code
        except PasswordResetCode.DoesNotExist:
            raise forms.ValidationError('Неверный код.')
        
        return code
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают.')
        
        return cleaned_data
    
    def save(self):
        """Сохраняет новый пароль и помечает код как использованный."""
        password = self.cleaned_data.get('new_password1')
        self.user.set_password(password)
        self.user.save()
        self.reset_code.mark_as_used()
        return self.user

