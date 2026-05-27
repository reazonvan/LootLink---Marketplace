/**
 * Service Worker LootLink: push-уведомления + offline-кеш статики.
 *
 * Стратегии:
 * - precache: бьём в кеш список критичных файлов на install.
 * - static: cache-first (быстро, фоном обновляем при HIT).
 * - navigations (HTML): network-first с fallback на /offline/ (если есть)
 *   или на закешированную корневую страницу.
 *
 * При выпуске новой версии увеличьте CACHE_VERSION — старые кеши
 * автоматически чистятся в activate.
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `lootlink-static-${CACHE_VERSION}`;
const RUNTIME_CACHE = `lootlink-runtime-${CACHE_VERSION}`;

const PRECACHE_URLS = [
    '/static/css/lootlink.css',
    '/static/css/catalog.css',
    '/static/js/catalog.js',
    '/static/js/favorites.js',
    '/static/js/search-autocomplete.js',
    '/static/img/logo.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(PRECACHE_URLS).catch(() => {
                // Один битый ресурс не должен ломать install целиком.
                return Promise.all(PRECACHE_URLS.map((u) => cache.add(u).catch(() => null)));
            }))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys
                    .filter((k) => k !== STATIC_CACHE && k !== RUNTIME_CACHE)
                    .map((k) => caches.delete(k))
            ))
            .then(() => clients.claim())
    );
});

function isStaticAsset(url) {
    return url.pathname.startsWith('/static/');
}

function isAuthOrApi(url) {
    return (
        url.pathname.startsWith('/accounts/') ||
        url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/admin/') ||
        url.pathname.startsWith('/ws/')
    );
}

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;

    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;

    // Не кешируем auth/API/admin/websocket — там нужны свежие данные
    // и есть session-cookie-зависимый контент.
    if (isAuthOrApi(url)) return;

    if (isStaticAsset(url)) {
        // cache-first для статики
        event.respondWith(
            caches.match(req).then((cached) => {
                if (cached) {
                    // Фоновое обновление
                    fetch(req).then((fresh) => {
                        if (fresh && fresh.ok) {
                            caches.open(STATIC_CACHE).then((c) => c.put(req, fresh.clone()));
                        }
                    }).catch(() => null);
                    return cached;
                }
                return fetch(req).then((fresh) => {
                    if (fresh && fresh.ok) {
                        const copy = fresh.clone();
                        caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
                    }
                    return fresh;
                });
            })
        );
        return;
    }

    if (req.mode === 'navigate') {
        // network-first для HTML-страниц
        event.respondWith(
            fetch(req)
                .then((resp) => {
                    if (resp && resp.ok) {
                        const copy = resp.clone();
                        caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy));
                    }
                    return resp;
                })
                .catch(() => caches.match(req).then((cached) => cached || caches.match('/')))
        );
    }
});

self.addEventListener('push', (event) => {
    let data = {
        title: 'LootLink',
        body: 'У вас новое уведомление',
        icon: '/static/img/logo.png',
        badge: '/static/img/badge.png',
        url: '/'
    };

    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (e) { /* ignore malformed push data */ }
    }

    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        data: {url: data.url},
        vibrate: [200, 100, 200],
        tag: 'lootlink-notification',
        requireInteraction: false
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (let client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus().then(() => {
                            if ('navigate' in client) {
                                return client.navigate(urlToOpen);
                            }
                        });
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});
