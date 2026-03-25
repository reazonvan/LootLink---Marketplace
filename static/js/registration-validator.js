document.addEventListener('DOMContentLoaded', function() {
    var usernameInput = document.querySelector('input[name="username"]');
    var emailInput = document.querySelector('input[name="email"]');
    var phoneInput = document.querySelector('input[name="phone"]');

    // Валидация только на странице регистрации - проверяем URL
    var isRegistrationPage = window.location.pathname.includes('/register');
    
    if (isRegistrationPage) {
        if (usernameInput) setupValidation(usernameInput, '/accounts/api/check-username/', 'username');
        if (emailInput) setupValidation(emailInput, '/accounts/api/check-email/', 'email');
        if (phoneInput) initPhoneMask(phoneInput);
    }

    initPasswordToggles();
});

/* ── Validation feedback ── */

function createFeedback(input) {
    // Проверяем, не существует ли уже feedback элемент
    var existing = input.nextElementSibling;
    if (existing && existing.classList.contains('field-feedback')) {
        return existing;
    }
    
    var el = document.createElement('div');
    el.className = 'field-feedback';
    input.parentNode.insertBefore(el, input.nextSibling);
    return el;
}

function setFeedback(el, input, type, text) {
    el.className = 'field-feedback field-feedback--' + type;
    el.textContent = '';
    if (type === 'loading') {
        var spinner = document.createElement('span');
        spinner.className = 'fb-spinner';
        el.appendChild(spinner);
        el.appendChild(document.createTextNode(' ' + text));
    } else if (type === 'ok') {
        el.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
        el.appendChild(document.createTextNode(' ' + text));
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else if (type === 'error') {
        el.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
        el.appendChild(document.createTextNode(' ' + text));
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
    } else {
        input.classList.remove('is-valid', 'is-invalid');
    }
}

function setupValidation(input, endpoint, fieldName) {
    // Защита от повторной инициализации
    if (input.hasAttribute('data-validation-initialized')) {
        return;
    }
    input.setAttribute('data-validation-initialized', 'true');
    
    var fb = createFeedback(input);
    var timer;

    input.addEventListener('input', function() {
        var val = this.value.trim();
        clearTimeout(timer);
        if (!val) { setFeedback(fb, input, 'clear', ''); return; }
        setFeedback(fb, input, 'loading', 'Проверка...');

        timer = setTimeout(function() {
            var param = fieldName;
            fetch(endpoint + '?' + param + '=' + encodeURIComponent(val), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.available) {
                    setFeedback(fb, input, 'ok', data.message);
                } else {
                    setFeedback(fb, input, 'error', data.message);
                }
            })
            .catch(function() {
                setFeedback(fb, input, 'error', 'Ошибка проверки');
            });
        }, 500);
    });
}

/* ── Phone mask +7 (XXX) XXX-XX-XX ── */

function initPhoneMask(input) {
    if (!input.value) input.value = '+7 ';

    input.addEventListener('focus', function() {
        if (!this.value) this.value = '+7 ';
    });

    input.addEventListener('input', function(e) {
        var raw = this.value.replace(/\D/g, '');

        if (raw.length === 0) { this.value = '+7 '; return; }

        if (raw[0] === '8') raw = '7' + raw.substring(1);
        if (raw[0] !== '7') raw = '7' + raw;
        if (raw.length > 11) raw = raw.substring(0, 11);

        var formatted = '+7';
        if (raw.length > 1) formatted += ' (' + raw.substring(1, Math.min(4, raw.length));
        if (raw.length >= 4) formatted += ') ';
        if (raw.length > 4) formatted += raw.substring(4, Math.min(7, raw.length));
        if (raw.length > 7) formatted += '-' + raw.substring(7, Math.min(9, raw.length));
        if (raw.length > 9) formatted += '-' + raw.substring(9, 11);

        this.value = formatted;
    });

    input.addEventListener('keydown', function(e) {
        var val = this.value;
        if (e.key === 'Backspace' && val.length <= 3) {
            e.preventDefault();
        }
    });

    var fb = createFeedback(input);
    setupValidation(input, '/accounts/api/check-phone/', 'phone');
}

/* ── Password visibility toggle ── */

function initPasswordToggles() {
    var pwFields = document.querySelectorAll('input[type="password"]');
    pwFields.forEach(function(input) {
        // Проверяем, не обработано ли уже это поле
        if (input.hasAttribute('data-toggle-initialized')) {
            return; // Уже обработано
        }
        
        // Проверяем, не обернуто ли уже поле
        if (input.parentNode.classList.contains('password-wrap')) {
            input.setAttribute('data-toggle-initialized', 'true');
            return;
        }
        
        // Отмечаем поле как обработанное ДО создания элементов
        input.setAttribute('data-toggle-initialized', 'true');
        
        var wrap = document.createElement('div');
        wrap.className = 'password-wrap';
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'password-toggle';
        btn.setAttribute('tabindex', '-1');
        btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
        wrap.appendChild(btn);

        btn.addEventListener('click', function() {
            var isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            this.innerHTML = isPassword
                ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
                : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
        });
    });
}
