/**
 * Lightbox с зумом для изображений листинга.
 *
 * Подключается ко всем <img class="gallery-zoomable"> или [data-zoom-src].
 * Клик — открывает изображение во фуллскрин-overlay. Закрытие: клик вне,
 * Esc, или кнопка закрытия. Поддерживает свайп вниз для закрытия на mobile.
 */
(function () {
    'use strict';

    var overlay = null;
    var imgEl = null;
    var lastFocus = null;

    function ensureOverlay() {
        if (overlay) return overlay;
        overlay = document.createElement('div');
        overlay.className = 'gallery-lightbox';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', 'Просмотр изображения');
        overlay.innerHTML =
            '<button type="button" class="gallery-lightbox__close" aria-label="Закрыть">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">' +
            '<path d="M6 6 L18 18 M18 6 L6 18"/></svg></button>' +
            '<img alt="">';
        document.body.appendChild(overlay);

        imgEl = overlay.querySelector('img');
        var closeBtn = overlay.querySelector('.gallery-lightbox__close');

        function close() {
            overlay.classList.remove('is-open');
            document.body.style.overflow = '';
            if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
        }

        closeBtn.addEventListener('click', close);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close();
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
        });

        // Swipe-to-close на мобильных
        var touchStartY = null;
        overlay.addEventListener('touchstart', function (e) {
            touchStartY = e.touches[0].clientY;
        }, { passive: true });
        overlay.addEventListener('touchmove', function (e) {
            if (touchStartY == null) return;
            var dy = e.touches[0].clientY - touchStartY;
            if (Math.abs(dy) > 80) { touchStartY = null; close(); }
        }, { passive: true });

        return overlay;
    }

    function open(src, alt) {
        ensureOverlay();
        imgEl.src = src;
        imgEl.alt = alt || '';
        overlay.classList.add('is-open');
        document.body.style.overflow = 'hidden';
        var closeBtn = overlay.querySelector('.gallery-lightbox__close');
        if (closeBtn) closeBtn.focus();
    }

    function attach(el) {
        if (el.dataset.zoomAttached === '1') return;
        el.dataset.zoomAttached = '1';
        if (!el.classList.contains('gallery-zoomable')) {
            el.classList.add('gallery-zoomable');
        }
        el.setAttribute('tabindex', '0');
        el.setAttribute('role', 'button');
        el.setAttribute('aria-label', 'Открыть изображение в полный размер');
        el.addEventListener('click', function () {
            lastFocus = el;
            var src = el.dataset.zoomSrc || el.getAttribute('src') || el.getAttribute('href');
            if (src) open(src, el.getAttribute('alt') || '');
        });
        el.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                el.click();
            }
        });
    }

    function init() {
        var nodes = document.querySelectorAll(
            '.gallery-zoomable, [data-zoom-src], .listing-detail-image, .listing-main-image img'
        );
        nodes.forEach(attach);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
