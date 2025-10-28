/**
 * Автоматическое форматирование номера телефона
 * Формат: +7 (999) 123-45-67
 */

function formatPhoneNumber(input) {
    // Удаляем все символы кроме цифр
    let cleaned = input.value.replace(/\D/g, '');
    
    // Если первая цифра не 7, добавляем её
    if (cleaned.length > 0 && cleaned[0] !== '7') {
        cleaned = '7' + cleaned;
    }
    
    // Ограничиваем длину до 11 цифр
    cleaned = cleaned.substring(0, 11);
    
    // Форматируем номер
    let formatted = '';
    
    if (cleaned.length > 0) {
        formatted = '+7';
        
        if (cleaned.length > 1) {
            formatted += ' (' + cleaned.substring(1, 4);
            
            if (cleaned.length > 4) {
                formatted += ') ' + cleaned.substring(4, 7);
                
                if (cleaned.length > 7) {
                    formatted += '-' + cleaned.substring(7, 9);
                    
                    if (cleaned.length > 9) {
                        formatted += '-' + cleaned.substring(9, 11);
                    }
                }
            }
        }
    }
    
    input.value = formatted;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Ищем поле телефона по ID или name
    const phoneInput = document.getElementById('id_phone') || 
                       document.querySelector('input[name="phone"]');
    
    if (phoneInput) {
        // Устанавливаем начальное значение +7
        if (!phoneInput.value || phoneInput.value === '') {
            phoneInput.value = '+7 (';
        }
        
        // Добавляем обработчики событий
        phoneInput.addEventListener('input', function(e) {
            formatPhoneNumber(this);
        });
        
        phoneInput.addEventListener('focus', function(e) {
            if (!this.value || this.value === '') {
                this.value = '+7 (';
            }
        });
        
        phoneInput.addEventListener('keydown', function(e) {
            // Запрещаем удаление +7
            if (e.key === 'Backspace' || e.key === 'Delete') {
                if (this.value.length <= 4) {
                    e.preventDefault();
                    this.value = '+7 (';
                }
            }
        });
        
        // Запрещаем вставку некорректных данных
        phoneInput.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            const cleaned = pastedText.replace(/\D/g, '');
            this.value = '';
            formatPhoneNumber(this);
            
            // Добавляем скопированные цифры
            for (let digit of cleaned) {
                const event = new Event('input', { bubbles: true });
                this.value += digit;
                formatPhoneNumber(this);
            }
        });
    }
});

