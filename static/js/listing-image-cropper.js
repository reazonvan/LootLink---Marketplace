/**
 * Listing Image Cropper with Rectangular Preview
 * Использует Cropper.js для обрезки фото объявлений
 */

class ListingImageCropper {
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
            <div class="modal fade" id="listingCropModal" tabindex="-1">
                <div class="modal-dialog modal-xl modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-crop"></i> Настройте изображение объявления
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-9">
                                    <div class="crop-container">
                                        <img id="listingCropImage" style="max-width: 100%;">
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="text-center">
                                        <p class="text-muted mb-2">Предпросмотр:</p>
                                        <div id="listingPreviewRect" class="mx-auto" style="width: 100%; height: 200px; overflow: hidden; border: 2px solid #dee2e6; border-radius: 8px;"></div>
                                        
                                        <div class="mt-3">
                                            <p class="small text-muted mb-2">Соотношение сторон:</p>
                                            <div class="btn-group-vertical w-100" role="group">
                                                <button type="button" class="btn btn-sm btn-outline-secondary aspect-ratio-btn" data-ratio="free">
                                                    <i class="bi bi-aspect-ratio"></i> Свободное
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary aspect-ratio-btn active" data-ratio="16/9">
                                                    16:9 (рекомендуется)
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary aspect-ratio-btn" data-ratio="4/3">
                                                    4:3
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary aspect-ratio-btn" data-ratio="1">
                                                    1:1 (квадрат)
                                                </button>
                                            </div>
                                        </div>
                                        
                                        <div class="mt-3">
                                            <button type="button" class="btn btn-sm btn-outline-secondary w-100 mb-2" id="listingRotateLeft">
                                                <i class="bi bi-arrow-counterclockwise"></i> Повернуть влево
                                            </button>
                                            <button type="button" class="btn btn-sm btn-outline-secondary w-100 mb-2" id="listingRotateRight">
                                                <i class="bi bi-arrow-clockwise"></i> Повернуть вправо
                                            </button>
                                        </div>
                                        
                                        <div class="mt-2">
                                            <div class="btn-group w-100" role="group">
                                                <button type="button" class="btn btn-sm btn-outline-secondary" id="listingZoomIn">
                                                    <i class="bi bi-zoom-in"></i>
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary" id="listingZoomOut">
                                                    <i class="bi bi-zoom-out"></i>
                                                </button>
                                                <button type="button" class="btn btn-sm btn-outline-secondary" id="listingReset">
                                                    <i class="bi bi-arrow-clockwise"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                            <button type="button" class="btn btn-primary" id="listingCropConfirm">
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
        const modal = document.getElementById('listingCropModal');
        
        // Поворот
        document.getElementById('listingRotateLeft')?.addEventListener('click', () => {
            this.cropper?.rotate(-45);
        });
        
        document.getElementById('listingRotateRight')?.addEventListener('click', () => {
            this.cropper?.rotate(45);
        });
        
        // Zoom
        document.getElementById('listingZoomIn')?.addEventListener('click', () => {
            this.cropper?.zoom(0.1);
        });
        
        document.getElementById('listingZoomOut')?.addEventListener('click', () => {
            this.cropper?.zoom(-0.1);
        });
        
        // Reset
        document.getElementById('listingReset')?.addEventListener('click', () => {
            this.cropper?.reset();
        });
        
        // Aspect ratio buttons
        document.querySelectorAll('.aspect-ratio-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ratio = e.currentTarget.dataset.ratio;
                this.changeAspectRatio(ratio);
                
                // Update active button
                document.querySelectorAll('.aspect-ratio-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
            });
        });
        
        // Confirm
        document.getElementById('listingCropConfirm')?.addEventListener('click', () => {
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
    
    changeAspectRatio(ratio) {
        if (!this.cropper) return;
        
        let aspectRatio = NaN; // Free aspect
        
        if (ratio === '16/9') {
            aspectRatio = 16 / 9;
        } else if (ratio === '4/3') {
            aspectRatio = 4 / 3;
        } else if (ratio === '1') {
            aspectRatio = 1;
        }
        
        this.cropper.setAspectRatio(aspectRatio);
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Проверка типа файла
        if (!file.type.match('image.*')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }
        
        // Проверка размера (5MB для объявлений)
        if (file.size > 5 * 1024 * 1024) {
            alert('Размер файла не должен превышать 5 МБ');
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
        const modalElement = document.getElementById('listingCropModal');
        const modal = new bootstrap.Modal(modalElement);
        const image = document.getElementById('listingCropImage');
        
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
                        aspectRatio: 16 / 9,
                        viewMode: 1,
                        dragMode: 'move',
                        autoCropArea: 0.95, // 95% для объявлений - показываем больше
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
                        preview: '#listingPreviewRect',
                        minCropBoxWidth: 100,
                        minCropBoxHeight: 75,
                        zoomOnWheel: true,
                        zoomOnTouch: true,
                        ready: function() {
                            // Принудительно включаем crop mode и центрируем
                            this.cropper.crop();
                            
                            // ФИКС: Центрируем crop box для объявлений
                            const containerData = this.cropper.getContainerData();
                            const cropBoxWidth = containerData.width * 0.9;
                            const cropBoxHeight = cropBoxWidth * (9 / 16); // 16:9 ratio
                            
                            this.cropper.setCropBoxData({
                                left: (containerData.width - cropBoxWidth) / 2,
                                top: (containerData.height - cropBoxHeight) / 2,
                                width: cropBoxWidth,
                                height: cropBoxHeight
                            });
                            
                        },
                        cropstart: function(e) {
                        },
                        cropmove: function(e) {
                            // ФИКС: Принудительно обновляем preview
                            const previewElement = document.getElementById('listingPreviewRect');
                            if (previewElement) {
                                previewElement.style.display = 'block';
                            }
                        }
                    });
                    
                    // Дополнительно включаем crop mode через 100ms
                        setTimeout(() => {
                            if (this.cropper) {
                                this.cropper.crop();
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
            maxWidth: 1200,
            maxHeight: 800,
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
            bootstrap.Modal.getInstance(document.getElementById('listingCropModal')).hide();
        }, 'image/jpeg', 0.9);
    }
    
    showPreview(imageUrl) {
        if (!this.previewContainer) return;
        
        this.previewContainer.innerHTML = `
            <div class="mt-3">
                <p class="text-muted mb-2">Выбранное изображение:</p>
                <img src="${imageUrl}" alt="Preview" class="img-thumbnail" style="max-width: 400px; max-height: 300px; border-radius: 8px;">
            </div>
        `;
    }
}

// Автоинициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Ищем input для изображения объявления
    const listingImageInput = document.getElementById('id_image');
    if (listingImageInput) {
        new ListingImageCropper('id_image', 'listingImagePreviewContainer');
    }
});

