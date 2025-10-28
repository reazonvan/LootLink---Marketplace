/**
 * Всплывающие уведомления в правом верхнем углу
 * Toast показываются только для НОВЫХ событий, НЕ при обновлении страницы
 */

// Флаг для предотвращения дублирования
let toastSystemInitialized = false;

// Создаём контейнер для toast уведомлений
document.addEventListener('DOMContentLoaded', function() {
    // Предотвращаем повторную инициализацию
    if (toastSystemInitialized) {
        console.log('⚠️ Toast система уже инициализирована, пропускаем');
        return;
    }
    toastSystemInitialized = true;
    
    console.log('🔔 Toast notifications initialized');
    
    // Создаём контейнер для toast если его нет
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed';
        toastContainer.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 99999;
            pointer-events: none;
        `;
        document.body.appendChild(toastContainer);
        console.log('✅ Toast container создан');
    }
    
    // СКРЫВАЕМ Django messages (не показываем их как Toast)
    // Все уведомления теперь через систему Notification
    const djangoMessages = document.querySelectorAll('.django-messages-data .alert');
    if (djangoMessages.length > 0) {
        console.log(`📨 Django messages скрыты: ${djangoMessages.length}`);
        djangoMessages.forEach(alert => alert.remove());
        
        const messagesContainer = document.querySelector('.django-messages-data');
        if (messagesContainer) {
            messagesContainer.remove();
        }
    }
    
    // Проверяем новые уведомления через AJAX
    if (typeof updateNotificationBadge !== 'undefined') {
        checkNewNotifications();
    }
});

/**
 * Проверка новых уведомлений (для real-time Toast)
 */
function checkNewNotifications() {
    // Получаем timestamp последней проверки из localStorage
    const lastCheck = localStorage.getItem('lastNotificationCheck');
    const now = Date.now();
    
    // Проверяем только если прошло более 10 секунд с последней проверки
    if (lastCheck && (now - parseInt(lastCheck)) < 10000) {
        return;
    }
    
    // Сохраняем текущее время
    localStorage.setItem('lastNotificationCheck', now.toString());
    
    // TODO: В будущем можно добавить AJAX запрос для проверки новых уведомлений
    // и показывать Toast только для действительно НОВЫХ уведомлений
}

/**
 * Показать toast уведомление
 */
function showToast(message, type = 'info', icon = 'info-circle', bgClass = 'bg-primary') {
    const toastContainer = document.getElementById('toast-container');
    
    const toastId = 'toast-' + Date.now();
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="4000">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${icon} me-2"></i>
                    <strong>${message}</strong>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Удаляем элемент после скрытия
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Глобальная функция для программного показа уведомлений
window.showToast = showToast;

