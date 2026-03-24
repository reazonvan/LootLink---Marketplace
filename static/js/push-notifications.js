/**
 * Web Push Notifications Manager
 */

class PushNotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.vapidPublicKey = null;
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications are not supported');
            return false;
        }

        try {
            this.registration = await navigator.serviceWorker.register('/static/js/service-worker.js');
            console.log('Service Worker registered');

            const response = await fetch('/accounts/push/vapid-key/');
            const data = await response.json();
            this.vapidPublicKey = data.publicKey;

            await this.checkSubscriptionStatus();
            return true;
        } catch (error) {
            console.error('Failed to initialize push notifications:', error);
            return false;
        }
    }

    async checkSubscriptionStatus() {
        try {
            const subscription = await this.registration.pushManager.getSubscription();
            const button = document.getElementById('push-notification-toggle');

            if (button) {
                if (subscription) {
                    button.textContent = 'Отключить уведомления';
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-secondary');
                } else {
                    button.textContent = 'Включить уведомления';
                    button.classList.remove('btn-secondary');
                    button.classList.add('btn-primary');
                }
            }
            return subscription !== null;
        } catch (error) {
            console.error('Failed to check subscription status:', error);
            return false;
        }
    }

    async requestPermission() {
        if (!this.isSupported) {
            alert('Ваш браузер не поддерживает push-уведомления');
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('Notification permission granted');
                return true;
            } else if (permission === 'denied') {
                alert('Вы запретили уведомления. Измените настройки браузера, чтобы включить их.');
                return false;
            }
            return false;
        } catch (error) {
            console.error('Failed to request permission:', error);
            return false;
        }
    }

    async subscribe() {
        try {
            if (Notification.permission !== 'granted') {
                const granted = await this.requestPermission();
                if (!granted) return false;
            }

            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });

            const response = await fetch('/accounts/push/subscribe/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subscription: subscription.toJSON()})
            });

            const data = await response.json();
            if (data.success) {
                console.log('Successfully subscribed to push notifications');
                await this.checkSubscriptionStatus();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to subscribe to push notifications:', error);
            return false;
        }
    }

    async unsubscribe() {
        try {
            const subscription = await this.registration.pushManager.getSubscription();
            if (!subscription) return true;

            await subscription.unsubscribe();

            const response = await fetch('/accounts/push/unsubscribe/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({endpoint: subscription.endpoint})
            });

            const data = await response.json();
            if (data.success) {
                console.log('Successfully unsubscribed from push notifications');
                await this.checkSubscriptionStatus();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to unsubscribe from push notifications:', error);
            return false;
        }
    }

    async toggle() {
        const subscription = await this.registration.pushManager.getSubscription();
        return subscription ? await this.unsubscribe() : await this.subscribe();
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
}

const pushManager = new PushNotificationManager();

document.addEventListener('DOMContentLoaded', async () => {
    await pushManager.init();
    const toggleButton = document.getElementById('push-notification-toggle');
    if (toggleButton) {
        toggleButton.addEventListener('click', async (e) => {
            e.preventDefault();
            const button = e.target;
            button.disabled = true;
            button.textContent = 'Обработка...';
            await pushManager.toggle();
            button.disabled = false;
        });
    }
});
