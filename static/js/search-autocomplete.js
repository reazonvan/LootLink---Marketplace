/**
 * Search autocomplete для строки поиска.
 *
 * Подключается ко всем формам с класса .search-box или .search-form
 * (имеющим input[name="q"]). Делает дебаунс-запросы к /api/search/suggest/
 * и показывает выпадающий список с играми и листингами.
 *
 * Recent searches хранятся в localStorage (ключ "lootlink:recent-searches",
 * до 5 записей).
 */
(function () {
    'use strict';

    var DEBOUNCE_MS = 220;
    var MIN_CHARS = 2;
    var ENDPOINT = '/api/search/suggest/';
    var RECENT_KEY = 'lootlink:recent-searches';
    var RECENT_LIMIT = 5;

    function getRecent() {
        try {
            var raw = localStorage.getItem(RECENT_KEY);
            if (!raw) return [];
            var arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr.slice(0, RECENT_LIMIT) : [];
        } catch (e) {
            return [];
        }
    }

    function pushRecent(query) {
        if (!query || query.length < MIN_CHARS) return;
        var recent = getRecent().filter(function (q) { return q !== query; });
        recent.unshift(query);
        try {
            localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, RECENT_LIMIT)));
        } catch (e) { /* quota — игнор */ }
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function buildPanel(input) {
        var panel = document.createElement('div');
        panel.className = 'search-suggest';
        panel.setAttribute('role', 'listbox');
        panel.hidden = true;
        // Позиционируется через CSS относительно ближайшего .search-box / form
        var host = input.closest('.search-box') || input.parentElement;
        if (host && getComputedStyle(host).position === 'static') {
            host.style.position = 'relative';
        }
        host.appendChild(panel);
        return panel;
    }

    function renderRecent(panel, recent) {
        if (!recent.length) {
            panel.hidden = true;
            return;
        }
        var html = '<div class="search-suggest__section">Недавние</div>';
        var iconHistory = '<svg class="search-suggest__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></svg>';
        recent.forEach(function (q) {
            html += '<a class="search-suggest__item" data-q="' + escapeHtml(q) + '">' +
                iconHistory +
                '<span>' + escapeHtml(q) + '</span></a>';
        });
        panel.innerHTML = html;
        panel.hidden = false;
    }

    function renderResults(panel, data, query) {
        var html = '';
        var iconGamepad = '<svg class="search-suggest__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="6" y1="11" x2="10" y2="11"/><line x1="8" y1="9" x2="8" y2="13"/><line x1="15" y1="12" x2="15.01" y2="12"/><line x1="18" y1="10" x2="18.01" y2="10"/><path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258A4 4 0 0 0 17.32 5z"/></svg>';
        var iconTag = '<svg class="search-suggest__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>';
        if (data.games && data.games.length) {
            html += '<div class="search-suggest__section">Игры</div>';
            data.games.forEach(function (g) {
                html += '<a class="search-suggest__item" href="/game/' + encodeURIComponent(g.slug) + '/">' +
                    iconGamepad +
                    '<span>' + escapeHtml(g.name) + '</span></a>';
            });
        }
        if (data.listings && data.listings.length) {
            html += '<div class="search-suggest__section">Объявления</div>';
            data.listings.forEach(function (l) {
                var meta = l.game__name ? ' · ' + escapeHtml(l.game__name) : '';
                html += '<a class="search-suggest__item" href="/listing/' + l.pk + '/">' +
                    iconTag +
                    '<span class="search-suggest__title">' + escapeHtml(l.title) + meta + '</span>' +
                    '<span class="search-suggest__price">' + escapeHtml(l.price) + ' ₽</span>' +
                    '</a>';
            });
        }
        if (!html) {
            html = '<div class="search-suggest__empty">Ничего не найдено по запросу «' + escapeHtml(query) + '»</div>';
        }
        panel.innerHTML = html;
        panel.hidden = false;
    }

    function attach(input) {
        if (input.dataset.suggestAttached === '1') return;
        input.dataset.suggestAttached = '1';
        input.setAttribute('autocomplete', 'off');

        var panel = buildPanel(input);
        var debounceId = null;
        var lastReq = 0;

        function close() { panel.hidden = true; }

        function doFetch(query) {
            var thisReq = ++lastReq;
            fetch(ENDPOINT + '?q=' + encodeURIComponent(query), {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (data) {
                    // Игнорируем устаревшие ответы (опередил более свежий запрос)
                    if (thisReq !== lastReq || !data) return;
                    renderResults(panel, data, query);
                })
                .catch(function () { /* network glitch — молча */ });
        }

        input.addEventListener('input', function () {
            var query = input.value.trim();
            clearTimeout(debounceId);
            if (query.length < MIN_CHARS) {
                renderRecent(panel, getRecent());
                return;
            }
            debounceId = setTimeout(function () { doFetch(query); }, DEBOUNCE_MS);
        });

        input.addEventListener('focus', function () {
            if (input.value.trim().length < MIN_CHARS) {
                renderRecent(panel, getRecent());
            }
        });

        // Сохраняем запрос при сабмите формы
        var form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function () {
                pushRecent(input.value.trim());
            });
        }

        // Клик по подсказке "недавнего" — заполняем input и сабмитим
        panel.addEventListener('click', function (e) {
            var item = e.target.closest('.search-suggest__item[data-q]');
            if (!item) return;
            e.preventDefault();
            input.value = item.dataset.q;
            if (form) form.submit();
        });

        // Закрываем при клике вне
        document.addEventListener('click', function (e) {
            if (!panel.contains(e.target) && e.target !== input) close();
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') close();
        });
    }

    function init() {
        var inputs = document.querySelectorAll(
            '.search-box input[name="q"], .search-form input[name="q"], #global-search-input'
        );
        inputs.forEach(attach);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
