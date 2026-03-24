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
            <div class="crop-modal-overlay" id="listingCropOverlay">
                <div class="crop-modal crop-modal--xl">
                    <div class="crop-modal__header">
                        <h3><i data-lucide="crop"></i> Настройте изображение объявления</h3>
                        <button type="button" class="crop-modal__close" id="listingCropClose">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    <div class="crop-modal__body">
                        <div class="crop-modal__layout crop-modal__layout--xl">
                            <div class="crop-container">
                                <img id="listingCropImage" style="max-width:100%;">
                            </div>
                            <div class="crop-modal__sidebar">
                                <div class="crop-modal__sidebar-label">Предпросмотр:</div>
                                <div id="listingPreviewRect"></div>

                                <div class="crop-modal__sidebar-label">Соотношение сторон:</div>
                                <div class="crop-aspect-group">
                                    <button type="button" class="btn btn-ghost btn-sm aspect-ratio-btn" data-ratio="free">
                                        <i data-lucide="maximize"></i> Свободное
                                    </button>
                                    <button type="button" class="btn btn-ghost btn-sm aspect-ratio-btn active" data-ratio="16/9">
                                        16:9 (рекомендуется)
                                    </button>
                                    <button type="button" class="btn btn-ghost btn-sm aspect-ratio-btn" data-ratio="4/3">
                                        4:3
                                    </button>
                                    <button type="button" class="btn btn-ghost btn-sm aspect-ratio-btn" data-ratio="1">
                                        1:1 (квадрат)
                                    </button>
                                </div>

                                <div class="crop-modal__controls">
                                    <div class="crop-modal__controls-row">
                                        <button type="button" class="btn btn-ghost btn-sm" id="listingRotateLeft">
                                            <i data-lucide="rotate-ccw"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="listingRotateRight">
                                            <i data-lucide="rotate-cw"></i>
                                        </button>
                                    </div>
                                    <div class="crop-modal__controls-row">
                                        <button type="button" class="btn btn-ghost btn-sm" id="listingZoomIn">
                                            <i data-lucide="zoom-in"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="listingZoomOut">
                                            <i data-lucide="zoom-out"></i>
                                        </button>
                                        <button type="button" class="btn btn-ghost btn-sm" id="listingReset">
                                            <i data-lucide="refresh-cw"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="crop-modal__footer">
                        <button type="button" class="btn btn-ghost" id="listingCropCancel">Отмена</button>
                        <button type="button" class="btn btn-primary" id="listingCropConfirm">
                            <i data-lucide="check"></i> Применить
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        this.overlay = document.getElementById('listingCropOverlay');
        if (typeof lucide !== 'undefined') lucide.createIcons({nodes: [this.overlay]});
        this.setupModalControls();
    }

    setupModalControls() {
        document.getElementById('listingRotateLeft')?.addEventListener('click', () => this.cropper?.rotate(-45));
        document.getElementById('listingRotateRight')?.addEventListener('click', () => this.cropper?.rotate(45));
        document.getElementById('listingZoomIn')?.addEventListener('click', () => this.cropper?.zoom(0.1));
        document.getElementById('listingZoomOut')?.addEventListener('click', () => this.cropper?.zoom(-0.1));
        document.getElementById('listingReset')?.addEventListener('click', () => this.cropper?.reset());
        document.getElementById('listingCropConfirm')?.addEventListener('click', () => this.cropImage());
        document.getElementById('listingCropClose')?.addEventListener('click', () => this.hideModal());
        document.getElementById('listingCropCancel')?.addEventListener('click', () => this.hideModal());

        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.hideModal();
        });

        document.querySelectorAll('#listingCropOverlay .aspect-ratio-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ratio = e.currentTarget.dataset.ratio;
                this.changeAspectRatio(ratio);
                document.querySelectorAll('#listingCropOverlay .aspect-ratio-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
            });
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

    changeAspectRatio(ratio) {
        if (!this.cropper) return;
        let aspectRatio = NaN;
        if (ratio === '16/9') aspectRatio = 16 / 9;
        else if (ratio === '4/3') aspectRatio = 4 / 3;
        else if (ratio === '1') aspectRatio = 1;
        this.cropper.setAspectRatio(aspectRatio);
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.type.match('image.*')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert('Размер файла не должен превышать 5 МБ');
            this.input.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => this.showCropModal(e.target.result);
        reader.readAsDataURL(file);
    }

    showCropModal(imageUrl) {
        const image = document.getElementById('listingCropImage');

        if (this.cropper) {
            this.cropper.destroy();
            this.cropper = null;
        }

        image.src = imageUrl;
        this.showModal();

        const initCropper = () => {
            this.cropper = new Cropper(image, {
                aspectRatio: 16 / 9,
                viewMode: 1,
                dragMode: 'move',
                autoCropArea: 0.95,
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
                    this.cropper.crop();
                    const containerData = this.cropper.getContainerData();
                    const cropBoxWidth = containerData.width * 0.9;
                    const cropBoxHeight = cropBoxWidth * (9 / 16);
                    this.cropper.setCropBoxData({
                        left: (containerData.width - cropBoxWidth) / 2,
                        top: (containerData.height - cropBoxHeight) / 2,
                        width: cropBoxWidth,
                        height: cropBoxHeight
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
            maxWidth: 1200,
            maxHeight: 800,
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
                <p style="font-size:var(--text-sm);color:var(--gray-500);margin-bottom:var(--space-2);">Выбранное изображение:</p>
                <img src="${imageUrl}" alt="Preview" style="max-width:400px;max-height:300px;border-radius:var(--radius-md);border:2px solid var(--gray-200);">
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const listingImageInput = document.getElementById('id_image');
    if (listingImageInput) {
        new ListingImageCropper('id_image', 'listingImagePreviewContainer');
    }
});
