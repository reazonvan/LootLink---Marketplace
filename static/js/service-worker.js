/**
 * Service Worker для Push уведомлений и offline режима.
 */

const CACHE_NAME = 'lootlink-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
    '/static/js/main.js',
    '/static/favicon.svg'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Cache opened');
                return cache.addAll(urlsToCache);
            })
    );
});

// Активация
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Fetch - offline support
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Возвращаем из кэша если есть
                if (response) {
                    return response;
                }
                
                // Иначе делаем запрос
                return fetch(event.request);
            })
    );
});

// Push notifications
self.addEventListener('push', (event) => {
    console.log('Push received:', event);
    
    let data = {
        title: 'LootLink',
        body: 'Новое уведомление',
        icon: '/static/favicon.svg',
        url: '/'
    };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: '/static/favicon.svg',
        vibrate: [200, 100, 200],
        data: {
            url: data.url
        },
        actions: [
            {
                action: 'open',
                title: 'Открыть'
            },
            {
                action: 'close',
                title: 'Закрыть'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        const url = event.notification.data.url || '/';
        event.waitUntil(
            clients.openWindow(url)
        );
    }
});

