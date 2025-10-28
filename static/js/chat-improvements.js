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
    console.log('💬 Chat improvements initialized');
    
    // 1. ОТПРАВКА ПО ENTER
    const messageForm = document.querySelector('#message-form');
    const messageTextarea = document.querySelector('#id_content');
    
    if (messageTextarea && messageForm) {
        console.log('✅ Найдена форма чата');
        
        messageTextarea.addEventListener('keydown', function(e) {
            // Enter без Shift = отправка
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('📤 Отправка по Enter');
                
                // Проверяем что есть текст
                if (this.value.trim()) {
                    messageForm.submit();
                } else {
                    console.log('⚠️ Пустое сообщение');
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
        console.log(`🔄 Автообновление для чата ${chatId}`);
        
        // ИСПРАВЛЕНИЕ Memory Leak - очищаем старый interval перед созданием нового
        if (window.chatInterval) {
            clearInterval(window.chatInterval);
            console.log('🧹 Очистка старого chat interval');
        }
        
        // Сохраняем interval ID
        window.chatInterval = setInterval(function() {
            loadNewMessages(chatId);
        }, 3000); // 3 секунды
        
        // Очищаем interval при уходе со страницы (beforeunload)
        window.addEventListener('beforeunload', function() {
            if (window.chatInterval) {
                clearInterval(window.chatInterval);
                console.log('🧹 Chat interval очищен при beforeunload');
            }
        });
        
        // ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: Очищаем при переходе на другую страницу (pagehide)
        window.addEventListener('pagehide', function() {
            if (window.chatInterval) {
                clearInterval(window.chatInterval);
                console.log('🧹 Chat interval очищен при pagehide');
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
                        console.log('🧹 Chat interval очищен по таймауту (страница скрыта 5+ минут)');
                    }
                }, 5 * 60 * 1000); // 5 минут
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
    .then(response => response.json())
    .then(data => {
        if (data.messages && data.messages.length > 0) {
            console.log(`📬 Получено новых сообщений: ${data.messages.length}`);
            
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
    .catch(error => {
        console.error('Ошибка загрузки сообщений:', error);
    });
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
    function showToast(message, type = 'info', icon = 'info-circle', bgClass = 'bg-primary') {
        console.log('Toast fallback:', message);
    }
}
