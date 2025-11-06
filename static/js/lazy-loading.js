/**
 * Lazy loading изображений для улучшения производительности.
 */

class LazyLoader {
    constructor() {
        this.images = document.querySelectorAll('img[data-src]');
        this.init();
    }
    
    init() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.loadImage(entry.target);
                        this.observer.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px'  // Загружаем немного заранее
            });
            
            this.images.forEach(img => this.observer.observe(img));
        } else {
            // Fallback для старых браузеров
            this.images.forEach(img => this.loadImage(img));
        }
    }
    
    loadImage(img) {
        const src = img.dataset.src;
        if (!src) return;
        
        // Показываем placeholder пока загружается
        img.style.background = '#f0f0f0';
        
        const tempImg = new Image();
        tempImg.onload = () => {
            img.src = src;
            img.removeAttribute('data-src');
            img.classList.add('loaded');
        };
        tempImg.src = src;
    }
}

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new LazyLoader());
} else {
    new LazyLoader();
}

