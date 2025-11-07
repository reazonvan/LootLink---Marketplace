/**
 * Улучшения для чата
 * 1. Отправка по Enter
 * 2. Автообновление сообщений
 * 3. Скролл к последнему сообщению
 */

// Получение CSRF токена из cookies
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

document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.querySelector('#message-form');
    const messageTextarea = document.querySelector('#id_content');
    
    if (messageTextarea && messageForm) {
        messageTextarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.value.trim()) {
                    messageForm.submit();
                }
            }
        });
        
        // Подсказка
        messageTextarea.placeholder = 'Введите сообщение... (Enter - отправить, Shift+Enter - новая строка)';
    }
    
    // 2. АВТООБНОВЛЕНИЕ СООБЩЕНИЙ (каждые 3 секунды)
    const messagesContainer = document.querySelector('.messages-list');
    const conversationId = document.querySelector('[data-conversation-id]');
    
    if (messagesContainer && conversationId) {
        const chatId = conversationId.getAttribute('data-conversation-id');
        
        if (window.chatInterval) {
            clearInterval(window.chatInterval);
        }
        
        // Сохраняем interval ID
        window.chatInterval = setInterval(function() {
            loadNewMessages(chatId);
        }, 3000); // 3 секунды
        
        window.addEventListener('beforeunload', function() {
            if (window.chatInterval) {
                clearInterval(window.chatInterval);
            }
        });
        
        window.addEventListener('pagehide', function() {
            if (window.chatInterval) {
                clearInterval(window.chatInterval);
            }
        });
        
        // ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: Очищаем при потере фокуса на 5+ минут
        let visibilityTimer = null;
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                // Страница скрыта - ставим таймер на 5 минут
                visibilityTimer = setTimeout(function() {
                    if (window.chatInterval) {
                        clearInterval(window.chatInterval);
                    }
                }, 5 * 60 * 1000);
            } else {
                // Страница снова видима - отменяем таймер
                if (visibilityTimer) {
                    clearTimeout(visibilityTimer);
                    visibilityTimer = null;
                }
            }
        });
    }
    
    // 3. СКРОЛЛ К ПОСЛЕДНЕМУ СООБЩЕНИЮ
    scrollToBottom();
});

/**
 * Загрузка новых сообщений через AJAX
 */
function loadNewMessages(conversationId) {
    const lastMessageId = getLastMessageId();
    const csrftoken = getCookie('csrftoken');
    
    fetch(`/chat/api/messages/${conversationId}/?after=${lastMessageId}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(message => {
                addMessageToChat(message);
            });
            
            scrollToBottom();
            
            // Toast уведомление о новом сообщении
            if (data.messages.length > 0 && !data.messages[0].is_own) {
                // Экранируем имя отправителя
                const safeSender = escapeHtml(data.messages[0].sender);
                showToast(`Новое сообщение от ${safeSender}`, 'info', 'chat', 'bg-primary');
            }
        }
    })
    .catch(() => {});
}

/**
 * Получить ID последнего сообщения
 */
function getLastMessageId() {
    const messages = document.querySelectorAll('[data-message-id]');
    if (messages.length > 0) {
        return messages[messages.length - 1].getAttribute('data-message-id');
    }
    return 0;
}

/**
 * Экранирование HTML для предотвращения XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Добавить сообщение в чат
 */
function addMessageToChat(message) {
    const messagesContainer = document.querySelector('.messages-list');
    
    // ВАЖНО: Экранируем контент для защиты от XSS
    const safeContent = escapeHtml(message.content);
    const safeSender = escapeHtml(message.sender);
    const safeTime = escapeHtml(message.created_at);
    
    const messageHTML = `
        <div class="message ${message.is_own ? 'message-own' : 'message-other'}" data-message-id="${message.id}">
            <div class="message-content">
                <div class="message-text">${safeContent}</div>
                <div class="message-time">${safeTime}</div>
            </div>
        </div>
    `;
    
    messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
}

/**
 * Скролл к последнему сообщению
 */
function scrollToBottom() {
    const messagesContainer = document.querySelector('.messages-list');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

/**
 * Показать уведомление (из toast-notifications.js)
 */
if (typeof showToast === 'undefined') {
    function showToast(message, type = 'info', icon = 'info-circle', bgClass = 'bg-primary') {}
}
