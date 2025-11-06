/**
 * Множественная загрузка изображений с предпросмотром и редактором.
 */

class MultiImageUploader {
    constructor(containerId, maxImages = 5) {
        this.container = document.getElementById(containerId);
        this.maxImages = maxImages;
        this.images = [];
        this.init();
    }
    
    init() {
        if (!this.container) return;
        
        this.createUI();
        this.attachEvents();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="image-upload-area">
                <div class="upload-grid" id="upload-grid">
                    <div class="upload-placeholder" id="upload-placeholder">
                        <input type="file" id="image-file-input" multiple accept="image/*" style="display:none;">
                        <label for="image-file-input" class="upload-label">
                            <i class="bi bi-cloud-upload" style="font-size: 48px;"></i>
                            <p>Нажмите или перетащите изображения</p>
                            <small>До ${this.maxImages} изображений, макс. 5 МБ каждое</small>
                        </label>
                    </div>
                </div>
                <div class="upload-progress" id="upload-progress" style="display:none;">
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" style="width: 0%;"></div>
                    </div>
                </div>
            </div>
        `;
    }
    
    attachEvents() {
        const fileInput = document.getElementById('image-file-input');
        const placeholder = document.getElementById('upload-placeholder');
        
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFiles(e.target.files);
            });
        }
        
        if (placeholder) {
            // Drag and drop
            placeholder.addEventListener('dragover', (e) => {
                e.preventDefault();
                placeholder.classList.add('drag-over');
            });
            
            placeholder.addEventListener('dragleave', () => {
                placeholder.classList.remove('drag-over');
            });
            
            placeholder.addEventListener('drop', (e) => {
                e.preventDefault();
                placeholder.classList.remove('drag-over');
                this.handleFiles(e.dataTransfer.files);
            });
        }
    }
    
    handleFiles(files) {
        if (this.images.length >= this.maxImages) {
            alert(`Максимум ${this.maxImages} изображений`);
            return;
        }
        
        const grid = document.getElementById('upload-grid');
        const placeholder = document.getElementById('upload-placeholder');
        
        Array.from(files).forEach((file, index) => {
            if (this.images.length >= this.maxImages) return;
            
            // Валидация
            if (!file.type.startsWith('image/')) {
                alert(`Файл ${file.name} не является изображением`);
                return;
            }
            
            if (file.size > 5 * 1024 * 1024) {
                alert(`Файл ${file.name} слишком большой (макс. 5 МБ)`);
                return;
            }
            
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const imageData = {
                    file: file,
                    dataUrl: e.target.result,
                    id: Date.now() + index
                };
                
                this.images.push(imageData);
                this.renderImagePreview(imageData, grid, placeholder);
                
                // Скрываем placeholder если достигнут лимит
                if (this.images.length >= this.maxImages) {
                    placeholder.style.display = 'none';
                }
            };
            
            reader.readAsDataURL(file);
        });
    }
    
    renderImagePreview(imageData, grid, placeholder) {
        const preview = document.createElement('div');
        preview.className = 'image-preview';
        preview.dataset.imageId = imageData.id;
        
        preview.innerHTML = `
            <img src="${imageData.dataUrl}" alt="Preview">
            <div class="image-controls">
                <button type="button" class="btn btn-sm btn-primary set-primary" title="Сделать главным">
                    <i class="bi bi-star"></i>
                </button>
                <button type="button" class="btn btn-sm btn-info zoom" title="Увеличить">
                    <i class="bi bi-zoom-in"></i>
                </button>
                <button type="button" class="btn btn-sm btn-danger remove" title="Удалить">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            ${this.images.indexOf(imageData) === 0 ? '<span class="primary-badge">Главное</span>' : ''}
        `;
        
        grid.insertBefore(preview, placeholder);
        
        // Events
        preview.querySelector('.remove').addEventListener('click', () => {
            this.removeImage(imageData.id);
        });
        
        preview.querySelector('.zoom').addEventListener('click', () => {
            this.showZoom(imageData.dataUrl);
        });
        
        preview.querySelector('.set-primary').addEventListener('click', () => {
            this.setPrimary(imageData.id);
        });
    }
    
    removeImage(imageId) {
        this.images = this.images.filter(img => img.id !== imageId);
        
        const preview = document.querySelector(`[data-image-id="${imageId}"]`);
        if (preview) preview.remove();
        
        // Показываем placeholder если есть место
        if (this.images.length < this.maxImages) {
            document.getElementById('upload-placeholder').style.display = 'block';
        }
    }
    
    setPrimary(imageId) {
        // Удаляем все бейджи
        document.querySelectorAll('.primary-badge').forEach(badge => badge.remove());
        
        // Находим индекс и перемещаем в начало
        const index = this.images.findIndex(img => img.id === imageId);
        if (index > 0) {
            const [image] = this.images.splice(index, 1);
            this.images.unshift(image);
        }
        
        // Добавляем бейдж
        const preview = document.querySelector(`[data-image-id="${imageId}"]`);
        if (preview) {
            const badge = document.createElement('span');
            badge.className = 'primary-badge';
            badge.textContent = 'Главное';
            preview.appendChild(badge);
        }
    }
    
    showZoom(imageUrl) {
        // Создаем модальное окно с зумом
        const modal = document.createElement('div');
        modal.className = 'image-zoom-modal';
        modal.innerHTML = `
            <div class="zoom-overlay">
                <button class="zoom-close">&times;</button>
                <img src="${imageUrl}" class="zoom-image" alt="Zoomed">
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on click
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('zoom-overlay') || e.target.classList.contains('zoom-close')) {
                modal.remove();
            }
        });
        
        // Close on ESC
        document.addEventListener('keydown', function closeOnEsc(e) {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', closeOnEsc);
            }
        });
    }
    
    getFiles() {
        return this.images.map(img => img.file);
    }
}

// CSS стили
const styles = `
<style>
.image-upload-area {
    margin: 20px 0;
}

.upload-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 15px;
}

.upload-placeholder {
    aspect-ratio: 1;
    border: 2px dashed #ccc;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s;
}

.upload-placeholder:hover,
.upload-placeholder.drag-over {
    border-color: #007bff;
    background: #f0f8ff;
}

.upload-label {
    text-align: center;
    cursor: pointer;
    padding: 20px;
}

.upload-label i {
    color: #007bff;
}

.image-preview {
    position: relative;
    aspect-ratio: 1;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.image-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.image-controls {
    position: absolute;
    top: 5px;
    right: 5px;
    display: flex;
    gap: 5px;
    opacity: 0;
    transition: opacity 0.3s;
}

.image-preview:hover .image-controls {
    opacity: 1;
}

.primary-badge {
    position: absolute;
    top: 5px;
    left: 5px;
    background: #ffc107;
    color: #000;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
}

.image-zoom-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
}

.zoom-overlay {
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.zoom-image {
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
    cursor: zoom-in;
}

.zoom-close {
    position: absolute;
    top: 20px;
    right: 20px;
    background: white;
    border: none;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-size: 24px;
    cursor: pointer;
    line-height: 1;
}

.zoom-close:hover {
    background: #f0f0f0;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', styles);

