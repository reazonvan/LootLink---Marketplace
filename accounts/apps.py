from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Аккаунты'

    def ready(self):
        from .models_badges import add_badges_method
        add_badges_method()

