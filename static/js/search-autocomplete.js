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
        recent.forEach(function (q) {
            html += '<a class="search-suggest__item" data-q="' + escapeHtml(q) + '">' +
                '<span class="search-suggest__icon" aria-hidden="true">↻</span>' +
                '<span>' + escapeHtml(q) + '</span></a>';
        });
        panel.innerHTML = html;
        panel.hidden = false;
    }

    function renderResults(panel, data, query) {
        var html = '';
        if (data.games && data.games.length) {
            html += '<div class="search-suggest__section">Игры</div>';
            data.games.forEach(function (g) {
                html += '<a class="search-suggest__item" href="/game/' + encodeURIComponent(g.slug) + '/">' +
                    '<span class="search-suggest__icon" aria-hidden="true">🎮</span>' +
                    '<span>' + escapeHtml(g.name) + '</span></a>';
            });
        }
        if (data.listings && data.listings.length) {
            html += '<div class="search-suggest__section">Объявления</div>';
            data.listings.forEach(function (l) {
                var meta = l.game__name ? ' · ' + escapeHtml(l.game__name) : '';
                html += '<a class="search-suggest__item" href="/listing/' + l.pk + '/">' +
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
