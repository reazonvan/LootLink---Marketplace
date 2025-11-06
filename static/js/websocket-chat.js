/**
 * WebSocket чат с real-time обновлениями
 */

class WebSocketChat {
    constructor(conversationId, userId, username) {
        this.conversationId = conversationId;
        this.userId = userId;
        this.username = username;
        this.socket = null;
        this.typingTimeout = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isTyping = false;
        
        this.init();
    }
    
    init() {
        this.connect();
        this.attachEventListeners();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('connected');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket closed:', event);
            this.showConnectionStatus('disconnected');
            
            // Попытка переподключения
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const timeout = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`Reconnecting in ${timeout}ms... (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connect(), timeout);
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('error');
        };
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'message':
                this.addMessage(data.message);
                break;
            case 'typing':
                this.showTypingIndicator(data.username, data.is_typing);
                break;
            case 'status':
                this.updateUserStatus(data.username, data.status);
                break;
            case 'read':
                this.markMessageAsRead(data.message_id);
                break;
            case 'error':
                console.error('Server error:', data.message);
                break;
        }
    }
    
    sendMessage(content) {
        if (!content.trim()) return;
        
        this.send({
            type: 'message',
            content: content.trim()
        });
    }
    
    sendTypingIndicator(isTyping) {
        this.send({
            type: 'typing',
            is_typing: isTyping
        });
    }
    
    sendReadReceipt(messageId) {
        this.send({
            type: 'read',
            message_id: messageId
        });
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected');
        }
    }
    
    addMessage(message) {
        const messagesContainer = document.getElementById('messages-container');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.sender_id === this.userId ? 'message-sent' : 'message-received'}`;
        messageDiv.dataset.messageId = message.id;
        
        const time = new Date(message.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">${this.escapeHtml(message.content)}</div>
                <div class="message-time">${time} ${message.is_read ? '✓✓' : '✓'}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Автоматически отмечаем как прочитанное
        if (message.sender_id !== this.userId) {
            this.sendReadReceipt(message.id);
        }
    }
    
    showTypingIndicator(username, isTyping) {
        let indicator = document.getElementById('typing-indicator');
        
        if (isTyping) {
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'typing-indicator';
                indicator.className = 'typing-indicator';
                indicator.innerHTML = `
                    <span class="typing-dots">
                        <span></span><span></span><span></span>
                    </span>
                    <span class="typing-text">${username} печатает...</span>
                `;
                document.getElementById('messages-container')?.appendChild(indicator);
                this.scrollToBottom();
            }
        } else {
            indicator?.remove();
        }
    }
    
    updateUserStatus(username, status) {
        const statusElement = document.getElementById('user-status');
        if (statusElement) {
            statusElement.textContent = status === 'online' ? 'Онлайн' : 'Оффлайн';
            statusElement.className = `user-status ${status}`;
        }
    }
    
    markMessageAsRead(messageId) {
        const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageDiv) {
            const timeElement = messageDiv.querySelector('.message-time');
            if (timeElement) {
                timeElement.innerHTML = timeElement.innerHTML.replace('✓', '✓✓');
            }
        }
    }
    
    showConnectionStatus(status) {
        const statusBar = document.getElementById('connection-status');
        if (statusBar) {
            statusBar.className = `connection-status ${status}`;
            statusBar.textContent = {
                'connected': 'Подключено',
                'disconnected': 'Отключено. Переподключение...',
                'error': 'Ошибка подключения'
            }[status] || '';
        }
    }
    
    attachEventListeners() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        if (messageInput) {
            messageInput.addEventListener('input', () => {
                // Индикатор печати
                if (!this.isTyping) {
                    this.isTyping = true;
                    this.sendTypingIndicator(true);
                }
                
                clearTimeout(this.typingTimeout);
                this.typingTimeout = setTimeout(() => {
                    this.isTyping = false;
                    this.sendTypingIndicator(false);
                }, 1000);
            });
            
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessageFromInput();
                }
            });
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessageFromInput();
            });
        }
    }
    
    sendMessageFromInput() {
        const messageInput = document.getElementById('message-input');
        if (!messageInput) return;
        
        const content = messageInput.value.trim();
        if (content) {
            this.sendMessage(content);
            messageInput.value = '';
            
            // Сбрасываем индикатор печати
            this.isTyping = false;
            this.sendTypingIndicator(false);
        }
    }
    
    scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// CSS стили для чата (добавить в отдельный файл или в head)
const chatStyles = `
<style>
.message {
    margin-bottom: 15px;
    display: flex;
}

.message-sent {
    justify-content: flex-end;
}

.message-received {
    justify-content: flex-start;
}

.message-bubble {
    max-width: 70%;
    padding: 10px 15px;
    border-radius: 18px;
    word-wrap: break-word;
}

.message-sent .message-bubble {
    background: #007bff;
    color: white;
}

.message-received .message-bubble {
    background: #e9ecef;
    color: #212529;
}

.message-time {
    font-size: 0.75rem;
    opacity: 0.7;
    margin-top: 5px;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    color: #6c757d;
    font-size: 0.9rem;
}

.typing-dots span {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6c757d;
    margin: 0 2px;
    animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% {
        transform: translateY(0);
    }
    30% {
        transform: translateY(-10px);
    }
}

.connection-status {
    padding: 5px 10px;
    font-size: 0.8rem;
    text-align: center;
}

.connection-status.connected {
    background: #d4edda;
    color: #155724;
}

.connection-status.disconnected {
    background: #fff3cd;
    color: #856404;
}

.connection-status.error {
    background: #f8d7da;
    color: #721c24;
}

.user-status {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8rem;
}

.user-status.online {
    background: #d4edda;
    color: #155724;
}

.user-status.offline {
    background: #e9ecef;
    color: #6c757d;
}
</style>
`;

