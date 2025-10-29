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
        .then(response => response.json())
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
                        showToast('success', data.message);
                    }
                } else {
                    // Удалено из избранного
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                    text.textContent = 'В избранное';
                    favoriteBtn.dataset.isFavorited = 'false';
                    
                    // Показываем уведомление
                    if (window.showToast) {
                        showToast('info', data.message);
                    }
                }
            } else {
                // Ошибка
                if (window.showToast) {
                    showToast('error', 'Произошла ошибка. Попробуйте позже.');
                }
            }
        })
        .catch(error => {
            console.error('Ошибка:', error);
            if (window.showToast) {
                showToast('error', 'Произошла ошибка соединения.');
            }
        })
        .finally(() => {
            // Включаем кнопку обратно
            favoriteBtn.disabled = false;
        });
    });
});

/**
 * Получение CSRF токена из cookies
 */
function getCookie(name) {
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

console.log('💖 Favorites script загружен');

