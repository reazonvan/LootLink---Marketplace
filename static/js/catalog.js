/* ============================================================
   LootLink — Catalog page JS
   Performance:
   - Никаких lucide.createIcons() для 770 элементов: иконка-плейсхолдер
     встроена через CSS background-image.
   - Категории не рендерятся в HTML: подгружаются AJAX по клику
     (endpoint: /listings/api/games/<slug>/categories/).
   - Кэш ответов в Map → повторное открытие мгновенное.
   ============================================================ */
(function () {
    'use strict';

    // ── DOM refs ──
    var input = document.getElementById('catSearchInput');
    var games = document.querySelectorAll('.cat-game');
    var sections = document.querySelectorAll('.cat-section');
    var noResult = document.getElementById('catNoResult');
    var abc = document.getElementById('catAbc');

    // ── Search ──
    if (input) {
        var searchTimer = null;
        input.addEventListener('input', function () {
            // Debounce 60ms — для 770 карточек реактивно достаточно
            if (searchTimer) clearTimeout(searchTimer);
            var q = this.value.trim().toLowerCase();
            searchTimer = setTimeout(function () {
                applyFilter(q);
            }, 60);
        });

        // Keyboard shortcut "/"
        document.addEventListener('keydown', function (e) {
            if (e.key === '/' && document.activeElement !== input && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                input.focus();
            }
            if (e.key === 'Escape' && document.activeElement === input) {
                input.value = '';
                applyFilter('');
                input.blur();
            }
        });
    }

    function applyFilter(q) {
        var found = 0;
        for (var i = 0; i < games.length; i++) {
            var g = games[i];
            var match = !q || g.dataset.name.indexOf(q) !== -1;
            g.classList.toggle('s-hidden', !match);
            if (match) found++;
        }
        for (var j = 0; j < sections.length; j++) {
            var s = sections[j];
            var visible = s.querySelectorAll('.cat-game:not(.s-hidden)');
            s.classList.toggle('s-hidden', visible.length === 0);
        }
        if (noResult) noResult.classList.toggle('visible', found === 0 && q.length > 0);
    }

    // ── Sticky alphabet header ──
    if (abc) {
        var sentinel = document.createElement('div');
        sentinel.style.height = '1px';
        sentinel.setAttribute('aria-hidden', 'true');
        abc.parentNode.insertBefore(sentinel, abc);
        var stickyObserver = new IntersectionObserver(function (entries) {
            abc.classList.toggle('stuck', !entries[0].isIntersecting);
        }, { threshold: 0, rootMargin: '-1px 0px 0px 0px' });
        stickyObserver.observe(sentinel);
    }

    // ── Active letter on scroll ──
    var abcBtns = document.querySelectorAll('.cat-abc__btn');
    if (abcBtns.length && sections.length) {
        var sectionObserver = new IntersectionObserver(function (entries) {
            for (var i = 0; i < entries.length; i++) {
                var entry = entries[i];
                if (entry.isIntersecting) {
                    var letter = entry.target.id.replace('letter-', '');
                    abcBtns.forEach(function (b) {
                        b.classList.toggle('active', b.dataset.letter === letter);
                    });
                }
            }
        }, { threshold: 0, rootMargin: '-80px 0px -70% 0px' });
        sections.forEach(function (s) { sectionObserver.observe(s); });
    }

    // ── Smooth scroll for alphabet links ──
    abcBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                var offset = abc ? abc.offsetHeight + 16 : 60;
                var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        });
    });

    // ── Lazy categories accordion ──
    // Кэш HTML-фрагментов категорий по slug игры.
    // Один fetch на игру за визит, повторное открытие — мгновенно.
    var categoriesCache = new Map();
    var apiUrlTemplate = (window.LL_CATALOG_CATEGORIES_URL || '/listings/api/games/__slug__/categories/');

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function buildCategoriesHtml(gameSlug, categories) {
        if (!categories || categories.length === 0) {
            return '<span class="cat-game__cats--empty">Категорий нет</span>';
        }
        var parts = [];
        for (var i = 0; i < categories.length; i++) {
            var c = categories[i];
            var url = '/listings/game/' + encodeURIComponent(gameSlug) +
                      '/category/' + encodeURIComponent(c.slug) + '/';
            var countBadge = c.listings_count
                ? '<span class="cat-tag__n">' + c.listings_count + '</span>'
                : '';
            parts.push(
                '<a class="cat-tag" href="' + url + '">' +
                    escapeHtml(c.name) + countBadge +
                '</a>'
            );
        }
        return parts.join('');
    }

    function loadCategories(toggleBtn) {
        var gameSlug = toggleBtn.dataset.gameSlug;
        var container = toggleBtn.nextElementSibling;
        if (!container || !container.classList.contains('cat-game__cats')) return;

        if (categoriesCache.has(gameSlug)) {
            container.innerHTML = categoriesCache.get(gameSlug);
            return Promise.resolve();
        }

        container.classList.add('cat-game__cats--loading');
        container.textContent = 'Загрузка...';

        var url = apiUrlTemplate.replace('__slug__', encodeURIComponent(gameSlug));
        return fetch(url, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        }).then(function (data) {
            var html = buildCategoriesHtml(gameSlug, data.categories || []);
            categoriesCache.set(gameSlug, html);
            container.classList.remove('cat-game__cats--loading');
            container.innerHTML = html;
        }).catch(function (err) {
            container.classList.remove('cat-game__cats--loading');
            container.innerHTML = '<span class="cat-game__cats--empty">Не удалось загрузить</span>';
            if (window.console) console.warn('catalog: failed to load categories', gameSlug, err);
        });
    }

    // Делегируем клик через document — экономим 770 listeners
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.cat-game__cats-toggle');
        if (!btn) return;
        e.preventDefault();
        var container = btn.nextElementSibling;
        if (!container) return;

        var expanded = btn.getAttribute('aria-expanded') === 'true';
        if (expanded) {
            btn.setAttribute('aria-expanded', 'false');
            container.hidden = true;
        } else {
            btn.setAttribute('aria-expanded', 'true');
            container.hidden = false;
            loadCategories(btn);
        }
    });
})();
