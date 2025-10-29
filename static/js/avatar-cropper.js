/**
 * Avatar Image Cropper with Circular Preview
 * Использует Cropper.js для обрезки аватарок
 */

class AvatarCropper {
    constructor(inputId, previewContainerId) {
        this.input = document.getElementById(inputId);
        this.previewContainer = document.getElementById(previewContainerId);
        this.cropper = null;
        this.croppedBlob = null;
        
        this.init();
    }
    
    init() {
        if (!this.input) return;
        
        // Создаем модальное окно для crop
        this.createCropModal();
        
        // Слушаем изменение input
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));
    }
    
    createCropModal() {
        const modalHtml = `
            <div class="modal fade" id="avatarCropModal" tabindex="-1">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-crop"></i> Настройте аватар
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="crop-container">
                                        <img id="avatarCropImage" style="max-width: 100%;">
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <p class="text-muted mb-2">Предпросмотр:</p>
                                        <div id="avatarPreviewCircle" class="mx-auto" style="width: 150px; height: 150px; border-radius: 50%; overflow: hidden; border: 2px solid #dee2e6;"></div>
                                        <div class="mt-3">
                                            <button type="button" class="btn btn-sm btn-outline-secondary" id="avatarRotateLeft">
                                                <i class="bi bi-arrow-counterclockwise"></i> Повернуть влево
                                            </button>
                                            <button type="button" class="btn btn-sm btn-outline-secondary" id="avatarRotateRight">
                                                <i class="bi bi-arrow-clockwise"></i> Повернуть вправо
                                            </button>
                                        </div>
                                        <div class="mt-2">
                                            <button type="button" class="btn btn-sm btn-outline-secondary" id="avatarZoomIn">
                                                <i class="bi bi-zoom-in"></i> +
                                            </button>
                                            <button type="button" class="btn btn-sm btn-outline-secondary" id="avatarZoomOut">
                                                <i class="bi bi-zoom-out"></i> -
                                            </button>
                                            <button type="button" class="btn btn-sm btn-outline-secondary" id="avatarReset">
                                                <i class="bi bi-arrow-clockwise"></i> Сброс
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                            <button type="button" class="btn btn-primary" id="avatarCropConfirm">
                                <i class="bi bi-check-circle"></i> Применить
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Добавляем обработчики для кнопок
        this.setupModalControls();
    }
    
    setupModalControls() {
        const modal = document.getElementById('avatarCropModal');
        
        // Поворот
        document.getElementById('avatarRotateLeft')?.addEventListener('click', () => {
            this.cropper?.rotate(-45);
        });
        
        document.getElementById('avatarRotateRight')?.addEventListener('click', () => {
            this.cropper?.rotate(45);
        });
        
        // Zoom
        document.getElementById('avatarZoomIn')?.addEventListener('click', () => {
            this.cropper?.zoom(0.1);
        });
        
        document.getElementById('avatarZoomOut')?.addEventListener('click', () => {
            this.cropper?.zoom(-0.1);
        });
        
        // Reset
        document.getElementById('avatarReset')?.addEventListener('click', () => {
            this.cropper?.reset();
        });
        
        // Confirm
        document.getElementById('avatarCropConfirm')?.addEventListener('click', () => {
            this.cropImage();
        });
        
        // Cleanup при закрытии
        modal.addEventListener('hidden.bs.modal', () => {
            if (this.cropper) {
                this.cropper.destroy();
                this.cropper = null;
            }
        });
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Проверка типа файла
        if (!file.type.match('image.*')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }
        
        // Проверка размера (2MB)
        if (file.size > 2 * 1024 * 1024) {
            alert('Размер файла не должен превышать 2 МБ');
            this.input.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.showCropModal(e.target.result);
        };
        reader.readAsDataURL(file);
    }
    
    showCropModal(imageUrl) {
        const modalElement = document.getElementById('avatarCropModal');
        const modal = new bootstrap.Modal(modalElement);
        const image = document.getElementById('avatarCropImage');
        
        // Уничтожаем старый cropper если есть
        if (this.cropper) {
            this.cropper.destroy();
            this.cropper = null;
        }
        
        // Устанавливаем изображение
        image.src = imageUrl;
        
        // Показываем модальное окно
        modal.show();
        
        // Инициализируем cropper после полной загрузки изображения
        modalElement.addEventListener('shown.bs.modal', () => {
            if (!this.cropper) {
                image.onload = () => {
                    this.cropper = new Cropper(image, {
                        aspectRatio: 1, // Квадрат для круглого аватара
                        viewMode: 1, // Crop box не может выходить за пределы canvas
                        dragMode: 'move',
                        autoCropArea: 0.9, // 90% области - оптимально для лица
                        restore: false,
                        guides: true,
                        center: true,
                        highlight: true,
                        background: true,
                        cropBoxMovable: true,
                        cropBoxResizable: true,
                        toggleDragModeOnDblclick: false,
                        responsive: true,
                        checkOrientation: true,
                        preview: '#avatarPreviewCircle',
                        minCropBoxWidth: 100,
                        minCropBoxHeight: 100,
                        initialAspectRatio: 1,
                        zoomOnWheel: true,
                        zoomOnTouch: true,
                        ready: function() {
                            console.log('Avatar Cropper готов');
                            // Принудительно включаем crop mode и центрируем
                            this.cropper.crop();
                            
                            // ФИКС: Центрируем crop box
                            const containerData = this.cropper.getContainerData();
                            const imageData = this.cropper.getImageData();
                            const cropBoxSize = Math.min(containerData.width, containerData.height) * 0.8;
                            
                            this.cropper.setCropBoxData({
                                left: (containerData.width - cropBoxSize) / 2,
                                top: (containerData.height - cropBoxSize) / 2,
                                width: cropBoxSize,
                                height: cropBoxSize
                            });
                            
                            console.log('Crop box центрирован');
                        },
                        cropstart: function(e) {
                            console.log('Crop start:', e.detail.action);
                        },
                        cropmove: function(e) {
                            console.log('Crop move');
                            // ФИКС: Принудительно обновляем preview при каждом движении
                            const previewElement = document.getElementById('avatarPreviewCircle');
                            if (previewElement) {
                                previewElement.style.display = 'block';
                            }
                        }
                    });
                    
                    // Дополнительно включаем crop mode через 100ms
                    setTimeout(() => {
                        if (this.cropper) {
                            this.cropper.crop();
                            console.log('Crop mode активирован');
                        }
                    }, 100);
                };
                
                // Если изображение уже загружено
                if (image.complete) {
                    image.onload();
                }
            }
        }, {once: true});
    }
    
    cropImage() {
        if (!this.cropper) return;
        
        // Получаем обрезанное изображение
        this.cropper.getCroppedCanvas({
            width: 300,
            height: 300,
            imageSmoothingEnabled: true,
            imageSmoothingQuality: 'high'
        }).toBlob((blob) => {
            // Создаем новый File объект
            const fileName = this.input.files[0].name;
            const croppedFile = new File([blob], fileName, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });
            
            // Создаем DataTransfer для замены файла в input
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(croppedFile);
            this.input.files = dataTransfer.files;
            
            // Показываем предпросмотр
            this.showPreview(URL.createObjectURL(blob));
            
            // Закрываем модальное окно
            bootstrap.Modal.getInstance(document.getElementById('avatarCropModal')).hide();
        }, 'image/jpeg', 0.9);
    }
    
    showPreview(imageUrl) {
        if (!this.previewContainer) return;
        
        this.previewContainer.innerHTML = `
            <div class="mt-3">
                <p class="text-muted mb-2">Выбранный аватар:</p>
                <img src="${imageUrl}" alt="Preview" class="img-thumbnail" style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover;">
            </div>
        `;
    }
}

// Автоинициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Ищем input для аватара
    const avatarInput = document.getElementById('id_avatar');
    if (avatarInput) {
        new AvatarCropper('id_avatar', 'avatarPreviewContainer');
    }
});

