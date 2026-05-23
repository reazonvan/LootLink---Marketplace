import logging

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser, PasswordResetCode, Profile

logger = logging.getLogger(__name__)


class HoneypotMixin:
    """
    Скрытое поле-ловушка для ботов.
    Настоящие пользователи не заполняют его (оно скрыто через CSS),
    а автоматические скрипты — заполняют.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["website"] = forms.CharField(
            required=False,
            widget=forms.TextInput(
                attrs={
                    "tabindex": "-1",
                    "autocomplete": "off",
                    "style": "position:absolute;left:-9999px;top:-9999px;",
                }
            ),
            label="",
        )

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            logger.warning("Honeypot triggered (bot detected)")
            raise forms.ValidationError("Обнаружена подозрительная активность.")
        return value


class CustomUserCreationForm(HoneypotMixin, UserCreationForm):
    """
    Форма регистрации нового пользователя.
    """

    consent = forms.BooleanField(
        required=True,
        label="Я согласен на обработку персональных данных",
        error_messages={
            "required": "Необходимо дать согласие на обработку персональных данных.",
        },
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email", "autocomplete": "email"}
        ),
    )
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Имя пользователя",
                "autocomplete": "username",
            }
        )
    )
    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+7 (999) 123-45-67",
                "autocomplete": "tel",
            }
        ),
        label="Телефон",
        help_text="Введите номер телефона. Он будет неизменным.",
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Пароль", "autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Повторите пароль",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email", "phone", "password1", "password2")

    def clean_username(self):
        """Проверка уникальности username (case-insensitive)."""
        username = self.cleaned_data.get("username")
        # Case-insensitive проверка (argear = Argear = ARGEAR)
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Пользователь с таким именем уже существует (регистр не учитывается)."
            )
        return username

    def clean_email(self):
        """Email-проверка case-insensitive. Нормализуем к lowercase."""
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_phone(self):
        """Валидация и нормализация номера телефона.

        Нормализуем формат перед проверкой уникальности, иначе
        '+7 (999) 123-45-67' и '89991234567' пройдут как разные значения.
        """
        import re

        from core.utils import clean_phone_number

        phone = self.cleaned_data.get("phone")
        if not phone:
            raise forms.ValidationError("Номер телефона обязателен для заполнения.")

        phone_digits = re.sub(r"\D", "", phone)
        if len(phone_digits) < 10 or len(phone_digits) > 11:
            raise forms.ValidationError(
                "Некорректный номер телефона. Введите номер в формате: +7 (999) 123-45-67"
            )
        if len(phone_digits) == 11 and phone_digits[0] not in ["7", "8"]:
            raise forms.ValidationError("Номер должен начинаться с 7 или 8")

        # Нормализуем номер к каноничному формату
        normalized = clean_phone_number(phone)

        # Проверка на уникальность по нормализованному номеру
        if Profile.objects.filter(phone=normalized).exists():
            raise forms.ValidationError("Пользователь с таким номером телефона уже существует.")

        return normalized

    def save(self, commit=True):
        """Создаёт пользователя; email/SMS уходят в Celery после commit.

        P2-3: до фикса email и SMS отправлялись синхронно — регистрация
        блокировалась на 5-15 секунд при медленном SMTP/SMS API.
        """
        user = super().save(commit=commit)
        if commit:
            from django.db import transaction as db_transaction

            user.profile.phone = self.cleaned_data.get("phone")
            user.profile.save(update_fields=["phone"])

            from .models import EmailVerification, PhoneVerification

            verification = EmailVerification.create_for_user(user)
            user_id = user.id
            token = verification.token
            phone = user.profile.phone

            def _send_async_notifications():
                import logging

                logger = logging.getLogger(__name__)
                try:
                    from core.integrations.email_service import EmailService

                    EmailService.send_verification_email_async(user_id, token)
                except AttributeError:
                    try:
                        from core.integrations.email_service import EmailService

                        EmailService.send_verification_email(user, token)
                    except Exception as e:
                        logger.error(f"Email verification отправка failed: {e}")
                except Exception as e:
                    logger.error(f"Email verification отправка failed: {e}")

                if phone:
                    try:
                        from core.integrations.sms_service import send_verification_sms

                        phone_verification = PhoneVerification.create_for_user(user, phone)
                        send_verification_sms(phone, phone_verification.code)
                    except Exception as e:
                        logger.error(f"SMS verification отправка failed: {e}")

            db_transaction.on_commit(_send_async_notifications)

        return user


class CustomAuthenticationForm(HoneypotMixin, AuthenticationForm):
    """
    Форма входа в систему.
    """

    username = forms.CharField(
        label="Имя пользователя или Email",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Имя пользователя или Email",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Пароль",
                "autocomplete": "current-password",
            }
        )
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
            self.fields["phone"].disabled = True
            self.fields["phone"].widget.attrs["readonly"] = "readonly"
            self.fields["phone"].help_text = "Телефон нельзя изменить после первого указания"

    class Meta:
        model = Profile
        fields = ["avatar", "bio", "phone"]
        widgets = {
            "bio": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Расскажите о себе..."}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7 (999) 123-45-67"}
            ),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }
        help_texts = {
            "phone": "Телефон можно указать один раз. После этого его нельзя будет изменить.",
        }

    def clean_bio(self):
        """Валидация описания профиля."""
        bio = self.cleaned_data.get("bio")
        if bio and len(bio) > 500:
            raise forms.ValidationError("Описание не должно превышать 500 символов.")
        return bio


# UserUpdateForm УДАЛЕНА - не используется, так как username и email нельзя изменить
# Вся функциональность редактирования профиля в ProfileUpdateForm


class PasswordResetRequestForm(forms.Form):
    """
    Форма запроса сброса пароля.
    Пользователь вводит email для получения кода.
    """

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Введите ваш email"}
        ),
        help_text="На этот email будет отправлен код подтверждения",
    )

    def clean_email(self):
        return self.cleaned_data.get("email")


class PasswordResetConfirmForm(forms.Form):
    """
    Форма подтверждения сброса пароля с кодом.
    """

    code = forms.CharField(
        label="Код подтверждения",
        max_length=8,
        min_length=8,
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-uppercase",
                "placeholder": "2A3B4C5D",
                "maxlength": "8",
                "style": "letter-spacing: 0.1em;",
            }
        ),
        help_text="Введите 8-символьный код из письма (буквы и цифры)",
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Новый пароль"}),
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Повторите пароль"}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_code(self):
        """Нормализация (UPPER, strip) + проверка attempts лимита."""
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if not self.user:
            raise forms.ValidationError("Ошибка валидации.")
        if not code:
            raise forms.ValidationError("Введите код.")

        # Самый свежий неиспользованный код пользователя
        reset_code = (
            PasswordResetCode.objects.filter(user=self.user, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if reset_code is None:
            raise forms.ValidationError("Код не найден. Запросите сброс заново.")

        if not reset_code.is_valid():
            raise forms.ValidationError("Код истёк или исчерпан лимит попыток.")

        if reset_code.code != code:
            reset_code.register_failed_attempt()
            remaining = max(0, PasswordResetCode.MAX_ATTEMPTS - reset_code.attempts)
            raise forms.ValidationError(f"Неверный код. Осталось попыток: {remaining}.")

        self.reset_code = reset_code
        return code

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают.")

        return cleaned_data

    def save(self):
        """Сохраняет новый пароль и помечает код как использованный."""
        password = self.cleaned_data.get("new_password1")
        self.user.set_password(password)
        self.user.save()
        self.reset_code.mark_as_used()
        return self.user


class ChangePasswordForm(forms.Form):
    """Форма смены пароля из настроек аккаунта."""

    current_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Введите текущий пароль",
                "autocomplete": "current-password",
            }
        ),
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Новый пароль",
                "autocomplete": "new-password",
            }
        ),
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Повторите новый пароль",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")
        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный текущий пароль.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Пароли не совпадают.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Пароль должен быть не менее 8 символов.")
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save()
        return self.user


class SMSVerificationForm(forms.Form):
    """Форма ввода SMS кода"""

    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Введите код из SMS",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg text-center",
                "placeholder": "000000",
                "pattern": "[0-9]{6}",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"]
        if not code.isdigit():
            raise forms.ValidationError("Код должен содержать только цифры")
        return code


class ResendVerificationForm(forms.Form):
    """Форма повторной отправки верификации"""

    pass


class DocumentVerificationForm(forms.ModelForm):
    """Форма загрузки документов для верификации"""

    class Meta:
        from .models import DocumentVerification

        model = DocumentVerification
        fields = ["document_type", "document_file"]
        widgets = {
            "document_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "document_file": forms.FileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.pdf"}
            ),
        }
        labels = {"document_type": "Тип документа", "document_file": "Файл документа"}
        help_texts = {"document_file": "Макс. 10 МБ. Форматы: JPG, PNG, PDF"}

    def clean_document_file(self):
        """Валидация файла документа через AttachmentValidator (размер + MIME)."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        from core.validators import AttachmentValidator

        file = self.cleaned_data.get("document_file")
        if file:
            try:
                AttachmentValidator(max_size_mb=10)(file)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return file
