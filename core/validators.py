"""
Кастомные валидаторы для Django моделей.
Включают глубокую проверку файлов через python-magic.
"""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image
import io

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning('python-magic не установлен! Используется базовая валидация файлов.')


@deconstructible
class SecureImageValidator:
    """
    Безопасный валидатор изображений.
    Проверяет:
    1. Размер файла
    2. Реальный MIME тип (через python-magic)
    3. Валидность изображения (через PIL)
    4. Расширение файла
    """
    
    def __init__(self, max_size_mb=5, allowed_extensions=None):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or ['jpg', 'jpeg', 'png', 'gif', 'webp']
        self.allowed_mime_types = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp'
        ]
    
    def __call__(self, file):
        """Основная валидация файла."""
        # 1. Проверка размера
        if file.size > self.max_size_bytes:
            raise ValidationError(
                f'Максимальный размер файла {self.max_size_mb} МБ. '
                f'Ваш файл: {file.size / (1024*1024):.2f} МБ'
            )
        
        # 2. Проверка расширения
        file_extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
        if file_extension not in self.allowed_extensions:
            raise ValidationError(
                f'Недопустимое расширение файла. '
                f'Разрешены: {", ".join(self.allowed_extensions)}'
            )
        
        # 3. Проверка реального MIME типа через python-magic
        if HAS_MAGIC:
            try:
                # Читаем первые 2048 байт для определения типа
                file.seek(0)
                file_start = file.read(2048)
                file.seek(0)
                
                mime = magic.from_buffer(file_start, mime=True)
                
                if mime not in self.allowed_mime_types:
                    raise ValidationError(
                        f'Файл не является изображением допустимого формата. '
                        f'Обнаружен тип: {mime}'
                    )
            except Exception as e:
                raise ValidationError(f'Ошибка при проверке типа файла: {str(e)}')
        
        # 4. Проверка валидности изображения через PIL
        try:
            file.seek(0)
            image = Image.open(file)
            image.verify()  # Проверяет что файл валидное изображение
            file.seek(0)  # Сбрасываем указатель после verify
            
            # Дополнительная проверка: пытаемся загрузить изображение
            image = Image.open(file)
            image.load()  # Принудительно загружаем данные
            file.seek(0)
            
            # Проверка на слишком большое разрешение (защита от декомпрессионной бомбы)
            max_pixels = 178_956_970  # ~4096x4096 * 10
            if image.size[0] * image.size[1] > max_pixels:
                raise ValidationError(
                    f'Разрешение изображения слишком большое. '
                    f'Максимум: {max_pixels} пикселей'
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f'Файл поврежден или не является валидным изображением: {str(e)}'
            )
        
        # 5. Проверка на наличие вредоносного кода в метаданных
        try:
            file.seek(0)
            image = Image.open(file)
            
            # Проверяем EXIF данные на наличие скриптов
            if hasattr(image, '_getexif') and image._getexif():
                exif_data = image._getexif()
                if exif_data:
                    for tag, value in exif_data.items():
                        if isinstance(value, (str, bytes)):
                            # Простая проверка на скрипты
                            dangerous_patterns = [b'<script', b'javascript:', b'<?php']
                            value_bytes = value if isinstance(value, bytes) else value.encode()
                            if any(pattern in value_bytes.lower() for pattern in dangerous_patterns):
                                raise ValidationError('Обнаружен потенциально вредоносный код в метаданных изображения')
            
            file.seek(0)
        except ValidationError:
            raise
        except Exception:
            # Если не можем прочитать EXIF - не критично
            pass
    
    def __eq__(self, other):
        return (
            isinstance(other, SecureImageValidator) and
            self.max_size_mb == other.max_size_mb and
            self.allowed_extensions == other.allowed_extensions
        )


@deconstructible
class AvatarValidator(SecureImageValidator):
    """Валидатор для аватаров пользователей."""
    
    def __init__(self):
        super().__init__(max_size_mb=2, allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])


@deconstructible
class ListingImageValidator(SecureImageValidator):
    """Валидатор для изображений объявлений."""
    
    def __init__(self):
        super().__init__(max_size_mb=5, allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])

