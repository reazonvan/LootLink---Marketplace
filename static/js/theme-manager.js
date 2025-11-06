/**
 * Менеджер темной/светлой темы
 */

class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }
    
    init() {
        // Применяем сохраненную тему
        this.applyTheme(this.currentTheme);
        
        // Создаем кнопку переключения
        this.createToggleButton();
        
        // Создаем кнопку "наверх"
        this.createScrollToTopButton();
    }
    
    createToggleButton() {
        const button = document.createElement('button');
        button.className = 'theme-toggle';
        button.id = 'theme-toggle';
        button.innerHTML = this.currentTheme === 'dark' ? '<i class="bi bi-sun-fill"></i>' : '<i class="bi bi-moon-fill"></i>';
        button.title = 'Переключить тему';
        
        button.addEventListener('click', () => this.toggle());
        
        document.body.appendChild(button);
    }
    
    createScrollToTopButton() {
        const button = document.createElement('button');
        button.className = 'scroll-to-top';
        button.id = 'scroll-to-top';
        button.innerHTML = '<i class="bi bi-arrow-up"></i>';
        button.title = 'Наверх';
        
        button.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
        
        // Показываем/скрываем при скролле
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                button.classList.add('visible');
            } else {
                button.classList.remove('visible');
            }
        });
        
        document.body.appendChild(button);
    }
    
    toggle() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        
        // Обновляем иконку
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.innerHTML = this.currentTheme === 'dark' ? '<i class="bi bi-sun-fill"></i>' : '<i class="bi bi-moon-fill"></i>';
        }
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }
}

// Auto-init
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});

