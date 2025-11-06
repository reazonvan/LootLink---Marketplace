"""
Оптимизация изображений: WebP конвертация, сжатие.
"""
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


def optimize_image(image_file, max_size=(1920, 1920), quality=85):
    """
    Оптимизация изображения.
    
    Args:
        image_file: Файл изображения
        max_size: Максимальные размеры (width, height)
        quality: Качество сжатия (1-100)
    
    Returns:
        bytes: Оптимизированное изображение
    """
    try:
        img = Image.open(image_file)
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Изменяем размер если больше максимума
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Сохраняем в буфер
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return output
        
    except Exception as e:
        logger.error(f'Image optimization error: {e}')
        return image_file


def convert_to_webp(image_file, quality=85):
    """
    Конвертация изображения в WebP.
    
    Args:
        image_file: Файл изображения
        quality: Качество (1-100)
    
    Returns:
        bytes: WebP изображение
    """
    try:
        img = Image.open(image_file)
        
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)
        output.seek(0)
        
        return output
        
    except Exception as e:
        logger.error(f'WebP conversion error: {e}')
        return image_file


def generate_thumbnails(image_file, sizes=None):
    """
    Генерация миниатюр разных размеров.
    
    Args:
        image_file: Файл изображения
        sizes: Список размеров [(width, height), ...]
    
    Returns:
        dict: {size: image_bytes}
    """
    if sizes is None:
        sizes = [(150, 150), (300, 300), (600, 600)]
    
    thumbnails = {}
    
    try:
        img = Image.open(image_file)
        
        for size in sizes:
            thumb = img.copy()
            thumb.thumbnail(size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            thumb.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            thumbnails[f'{size[0]}x{size[1]}'] = output
        
        return thumbnails
        
    except Exception as e:
        logger.error(f'Thumbnail generation error: {e}')
        return {}

