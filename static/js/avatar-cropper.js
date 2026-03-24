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
        this.overlay = null;

        this.init();
    }

    init() {
        if (!this.input) return;
        this.createCropModal();
        this.input.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    createCropModal() {
        const html = `
            <div class="crop-modal-overlay" id="avatarCropOverlay">
                <div class="crop-modal">
                    <div class="crop-modal__header">
                        <h3><i data-lucide="crop"></i> Настройте аватар</h3>
                        <button type="button" class="crop-modal__close" id="avatarCropClose">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    <div class="crop-modal__body">
                        <div class="crop-modal__layout">
                            <div class="crop-container">
                                <img id="avatarCropImage" style="max-width:100%;">
                            </div>
                            <div class="crop-modal__sidebar">
                                <div class="crop-modal__sidebar-label">Предпросмотр:</div>
                                <div id="avatarPreviewCircle"></div>
                                <div class="crop-modal__controls">
                                    <div class="crop-modal__controls-row">
                                        <button type="button" class="btn btn-ghost btn-sm" id="avatarRotateLeft">
                                            <i data-lucide="rotate-ccw"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="avatarRotateRight">
                                            <i data-lucide="rotate-cw"></i>
                                        </button>
                                    </div>
                                    <div class="crop-modal__controls-row">
                                        <button type="button" class="btn btn-ghost btn-sm" id="avatarZoomIn">
                                            <i data-lucide="zoom-in"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="avatarZoomOut">
                                            <i data-lucide="zoom-out"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="avatarReset">
                                            <i data-lucide="refresh-cw"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="crop-modal__footer">
                        <button type="button" class="btn btn-ghost" id="avatarCropCancel">Отмена</button>
                        <button type="button" class="btn btn-primary" id="avatarCropConfirm">
                            <i data-lucide="check"></i> Применить
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        this.overlay = document.getElementById('avatarCropOverlay');
        if (typeof lucide !== 'undefined') lucide.createIcons({nodes: [this.overlay]});
        this.setupModalControls();
    }

    setupModalControls() {
        document.getElementById('avatarRotateLeft')?.addEventListener('click', () => this.cropper?.rotate(-45));
        document.getElementById('avatarRotateRight')?.addEventListener('click', () => this.cropper?.rotate(45));
        document.getElementById('avatarZoomIn')?.addEventListener('click', () => this.cropper?.zoom(0.1));
        document.getElementById('avatarZoomOut')?.addEventListener('click', () => this.cropper?.zoom(-0.1));
        document.getElementById('avatarReset')?.addEventListener('click', () => this.cropper?.reset());
        document.getElementById('avatarCropConfirm')?.addEventListener('click', () => this.cropImage());
        document.getElementById('avatarCropClose')?.addEventListener('click', () => this.hideModal());
        document.getElementById('avatarCropCancel')?.addEventListener('click', () => this.hideModal());

        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.hideModal();
        });
    }

    showModal() {
        this.overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    hideModal() {
        this.overlay.classList.remove('active');
        document.body.style.overflow = '';
        if (this.cropper) {
            this.cropper.destroy();
            this.cropper = null;
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.type.match('image.*')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }

        if (file.size > 2 * 1024 * 1024) {
            alert('Размер файла не должен превышать 2 МБ');
            this.input.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => this.showCropModal(e.target.result);
        reader.readAsDataURL(file);
    }

    showCropModal(imageUrl) {
        const image = document.getElementById('avatarCropImage');

        if (this.cropper) {
            this.cropper.destroy();
            this.cropper = null;
        }

        image.src = imageUrl;
        this.showModal();

        const initCropper = () => {
            this.cropper = new Cropper(image, {
                aspectRatio: 1,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 0.9,
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
                zoomOnWheel: true,
                zoomOnTouch: true,
                ready: function() {
                    this.cropper.crop();
                    const containerData = this.cropper.getContainerData();
                    const cropBoxSize = Math.min(containerData.width, containerData.height) * 0.8;
                    this.cropper.setCropBoxData({
                        left: (containerData.width - cropBoxSize) / 2,
                        top: (containerData.height - cropBoxSize) / 2,
                        width: cropBoxSize,
                        height: cropBoxSize
                    });
                }
            });
        };

        if (image.complete && image.naturalWidth > 0) {
            setTimeout(initCropper, 50);
        } else {
            image.onload = () => setTimeout(initCropper, 50);
        }
    }

    cropImage() {
        if (!this.cropper) return;

        this.cropper.getCroppedCanvas({
            width: 300,
            height: 300,
            imageSmoothingEnabled: true,
            imageSmoothingQuality: 'high'
        }).toBlob((blob) => {
            const fileName = this.input.files[0].name;
            const croppedFile = new File([blob], fileName, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });

            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(croppedFile);
            this.input.files = dataTransfer.files;

            this.showPreview(URL.createObjectURL(blob));
            this.hideModal();
        }, 'image/jpeg', 0.9);
    }

    showPreview(imageUrl) {
        if (!this.previewContainer) return;
        this.previewContainer.innerHTML = `
            <div style="margin-top:var(--space-3);">
                <p style="font-size:var(--text-sm);color:var(--gray-500);margin-bottom:var(--space-2);">Выбранный аватар:</p>
                <img src="${imageUrl}" alt="Preview" style="width:150px;height:150px;border-radius:50%;object-fit:cover;border:2px solid var(--gray-200);">
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const avatarInput = document.getElementById('id_avatar');
    if (avatarInput) {
        new AvatarCropper('id_avatar', 'avatarPreviewContainer');
    }
});
