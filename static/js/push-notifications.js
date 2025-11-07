/**
 * Web Push Notifications (Service Worker).
 */

class PushNotifications {
    constructor() {
        this.vapidPublicKey = null;
        this.swRegistration = null;
        this.init();
    }
    
    async init() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            return;
        }
        
        try {
            this.swRegistration = await navigator.serviceWorker.register('/static/js/service-worker.js');
            
            // Запрашиваем VAPID ключ с сервера
            const response = await fetch('/api/push/vapid-public-key/');
            const data = await response.json();
            this.vapidPublicKey = data.public_key;
            
        } catch (error) {
        }
    }
    
    async requestPermission() {
        if (!('Notification' in window)) {
            alert('Ваш браузер не поддерживает уведомления');
            return false;
        }
        
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            await this.subscribe();
            return true;
        } else {
            return false;
        }
    }
    
    async subscribe() {
        try {
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            
            // Отправляем subscription на сервер
            await fetch('/notifications/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify(subscription.toJSON())
            });
            
            return true;
            
        } catch (error) {
            return false;
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    getCookie(name) {
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
}

// Auto-init
window.pushNotifications = new PushNotifications();

