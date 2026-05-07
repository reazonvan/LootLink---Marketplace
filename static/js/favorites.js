/**
 * Обработка избранного
 */

document.addEventListener('DOMContentLoaded', function() {
    const favoriteBtn = document.getElementById('favorite-btn');
    
    if (!favoriteBtn) return;
    
    favoriteBtn.addEventListener('click', function() {
        const listingId = this.dataset.listingId;
        const isFavorited = this.dataset.isFavorited === 'true';
        
        // Отключаем кнопку на время запроса
        favoriteBtn.disabled = true;
        
        // AJAX запрос
        fetch(`/listing/${listingId}/favorite/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('lootlink_csrftoken') || getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Обновляем состояние кнопки.
                // Проект использует Lucide-иконки, не Bootstrap Icons —
                // поэтому состояние "в избранном" выражается через
                // data-favorited атрибут + CSS-класс active.
                // CSS подсвечивает heart через fill: currentColor (см. lootlink.css).
                const text = document.getElementById('favorite-text');

                if (data.is_favorited) {
                    favoriteBtn.classList.add('active');
                    favoriteBtn.dataset.isFavorited = 'true';
                    if (text) text.textContent = 'В избранном';
                    if (window.showToast) {
                        showToast(data.message, 'success');
                    }
                } else {
                    favoriteBtn.classList.remove('active');
                    favoriteBtn.dataset.isFavorited = 'false';
                    if (text) text.textContent = 'В избранное';
                    if (window.showToast) {
                        showToast(data.message, 'info');
                    }
                }
            } else {
                if (window.showToast) {
                    showToast('Произошла ошибка. Попробуйте позже.', 'error');
                }
            }
        })
        .catch(() => {
            if (window.showToast) {
                showToast('Произошла ошибка соединения.', 'error');
            }
        })
        .finally(() => {
            // Включаем кнопку обратно
            favoriteBtn.disabled = false;
        });
    });
});

/**
 * Получение CSRF токена из meta тега или cookies
 */
function getCookie(name) {
    // Сначала пробуем из meta тега
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.content;
    }
    
    // Если нет в meta, пробуем из cookies
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


