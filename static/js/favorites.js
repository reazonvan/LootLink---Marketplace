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
                'X-CSRFToken': getCookie('csrftoken'),
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
                // Обновляем состояние кнопки
                const icon = favoriteBtn.querySelector('i');
                const text = document.getElementById('favorite-text');
                
                if (data.is_favorited) {
                    // Добавлено в избранное
                    icon.classList.remove('bi-heart');
                    icon.classList.add('bi-heart-fill');
                    text.textContent = 'В избранном';
                    favoriteBtn.dataset.isFavorited = 'true';
                    
                    // Показываем уведомление
                    if (window.showToast) {
                        showToast(data.message, 'success', 'heart-fill', 'bg-success');
                    }
                } else {
                    // Удалено из избранного
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                    text.textContent = 'В избранное';
                    favoriteBtn.dataset.isFavorited = 'false';
                    
                    // Показываем уведомление
                    if (window.showToast) {
                        showToast(data.message, 'info', 'heart', 'bg-info');
                    }
                }
            } else {
                // Ошибка
                if (window.showToast) {
                    showToast('Произошла ошибка. Попробуйте позже.', 'error', 'exclamation-triangle', 'bg-danger');
                }
            }
        })
        .catch(() => {
            if (window.showToast) {
                showToast('Произошла ошибка соединения.', 'error', 'exclamation-triangle', 'bg-danger');
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


