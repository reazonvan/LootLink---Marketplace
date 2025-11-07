/**
 * Валидация полей регистрации в реальном времени
 * Проверяет доступность username, email и phone через AJAX
 */

document.addEventListener('DOMContentLoaded', function() {
    // Получаем элементы формы регистрации
    const usernameInput = document.querySelector('input[name="username"]');
    const emailInput = document.querySelector('input[name="email"]');
    const phoneInput = document.querySelector('input[name="phone"]');
    
    // Создаем элементы для отображения сообщений валидации
    if (usernameInput) {
        setupValidation(usernameInput, '/accounts/api/check-username/', 'username');
    }
    
    if (emailInput) {
        setupValidation(emailInput, '/accounts/api/check-email/', 'email');
    }
    
    if (phoneInput) {
        setupValidation(phoneInput, '/accounts/api/check-phone/', 'phone');
    }
});

/**
 * Настраивает валидацию для поля ввода
 * @param {HTMLElement} input - Элемент поля ввода
 * @param {string} endpoint - URL для проверки
 * @param {string} fieldName - Имя поля для отображения
 */
function setupValidation(input, endpoint, fieldName) {
    // Создаем элемент для отображения сообщения
    const feedbackElement = document.createElement('div');
    feedbackElement.className = 'validation-feedback';
    feedbackElement.style.fontSize = '0.875rem';
    feedbackElement.style.marginTop = '0.25rem';
    
    // Вставляем элемент после input
    input.parentNode.insertBefore(feedbackElement, input.nextSibling);
    
    // Таймер для debounce (задержка перед отправкой запроса)
    let debounceTimer;
    
    // Обработчик события ввода
    input.addEventListener('input', function() {
        const value = this.value.trim();
        
        // Очищаем предыдущий таймер
        clearTimeout(debounceTimer);
        
        // Очищаем сообщение если поле пустое
        if (!value) {
            feedbackElement.textContent = '';
            feedbackElement.className = 'validation-feedback';
            input.classList.remove('is-valid', 'is-invalid');
            return;
        }
        
        // Показываем индикатор загрузки
        feedbackElement.textContent = 'Проверка...';
        feedbackElement.className = 'validation-feedback text-muted';
        input.classList.remove('is-valid', 'is-invalid');
        
        // Устанавливаем новый таймер (задержка 500ms)
        debounceTimer = setTimeout(() => {
            checkAvailability(value, endpoint, feedbackElement, input);
        }, 500);
    });
}

/**
 * Проверяет доступность значения через AJAX
 * @param {string} value - Значение для проверки
 * @param {string} endpoint - URL для проверки
 * @param {HTMLElement} feedbackElement - Элемент для отображения результата
 * @param {HTMLElement} input - Поле ввода
 */
function checkAvailability(value, endpoint, feedbackElement, input) {
    // Определяем параметр запроса на основе endpoint
    let param;
    if (endpoint.includes('username')) {
        param = 'username';
    } else if (endpoint.includes('email')) {
        param = 'email';
    } else if (endpoint.includes('phone')) {
        param = 'phone';
    }
    
    // Отправляем AJAX запрос
    fetch(`${endpoint}?${param}=${encodeURIComponent(value)}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.available) {
            // Значение доступно
            feedbackElement.textContent = '✓ ' + data.message;
            feedbackElement.className = 'validation-feedback text-success';
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        } else {
            // Значение недоступно или ошибка валидации
            feedbackElement.textContent = '✗ ' + data.message;
            feedbackElement.className = 'validation-feedback text-danger';
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
        }
    })
    .catch(error => {
        feedbackElement.textContent = 'Ошибка проверки. Попробуйте позже.';
        feedbackElement.className = 'validation-feedback text-warning';
        input.classList.remove('is-valid', 'is-invalid');
    });
}

