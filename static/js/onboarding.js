/**
 * Онбординг для новых пользователей
 */

class Onboarding {
    constructor() {
        this.steps = [
            {
                element: '.navbar',
                title: 'Добро пожаловать в LootLink! 👋',
                content: 'Давайте познакомимся с основными функциями сайта',
                position: 'bottom'
            },
            {
                element: '[href="/catalog/"]',
                title: 'Каталог игр 🎮',
                content: 'Здесь вы найдете все игры и товары',
                position: 'bottom'
            },
            {
                element: '[href="/search/"]',
                title: 'Поиск 🔍',
                content: 'Используйте глобальный поиск для быстрого нахождения товаров',
                position: 'bottom'
            },
            {
                element: '[href="/listing/create/"]',
                title: 'Создать объявление 📝',
                content: 'Разместите свой товар на продажу',
                position: 'bottom'
            },
            {
                element: '.dropdown-toggle',
                title: 'Ваш профиль 👤',
                content: 'Здесь находятся настройки, кошелек, аналитика и многое другое',
                position: 'bottom'
            }
        ];
        
        this.currentStep = 0;
        this.overlay = null;
        this.tooltip = null;
        
        this.init();
    }
    
    init() {
        // Проверяем показывали ли онбординг
        if (localStorage.getItem('onboarding_completed') === 'true') {
            return;
        }
        
        // Ждем загрузки страницы
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.start());
        } else {
            this.start();
        }
    }
    
    start() {
        this.createOverlay();
        this.showStep(0);
    }
    
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay';
        this.overlay.innerHTML = `
            <style>
            .onboarding-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                z-index: 9998;
                pointer-events: none;
            }
            
            .onboarding-highlight {
                position: relative;
                z-index: 9999 !important;
                box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.7);
                border-radius: 8px;
            }
            
            .onboarding-tooltip {
                position: absolute;
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
                max-width: 350px;
                z-index: 10000;
            }
            
            [data-theme="dark"] .onboarding-tooltip {
                background: #2d2d2d;
                color: #e9ecef;
            }
            
            .onboarding-tooltip h4 {
                margin: 0 0 10px 0;
                font-size: 18px;
            }
            
            .onboarding-tooltip p {
                margin: 0 0 15px 0;
                color: #6c757d;
            }
            
            [data-theme="dark"] .onboarding-tooltip p {
                color: #adb5bd;
            }
            
            .onboarding-actions {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .onboarding-progress {
                font-size: 12px;
                color: #6c757d;
            }
            </style>
        `;
        
        document.body.appendChild(this.overlay);
    }
    
    showStep(index) {
        if (index >= this.steps.length) {
            this.complete();
            return;
        }
        
        const step = this.steps[index];
        const element = document.querySelector(step.element);
        
        if (!element) {
            // Пропускаем если элемент не найден
            this.showStep(index + 1);
            return;
        }
        
        // Убираем предыдущее выделение
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
        
        // Выделяем текущий элемент
        element.classList.add('onboarding-highlight');
        
        // Создаем/обновляем тултип
        this.showTooltip(element, step, index);
    }
    
    showTooltip(element, step, index) {
        if (this.tooltip) {
            this.tooltip.remove();
        }
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'onboarding-tooltip';
        
        const isLast = index === this.steps.length - 1;
        
        this.tooltip.innerHTML = `
            <h4>${step.title}</h4>
            <p>${step.content}</p>
            <div class="onboarding-actions">
                <span class="onboarding-progress">${index + 1} / ${this.steps.length}</span>
                <div>
                    <button class="btn btn-sm btn-outline-secondary me-2" id="onboarding-skip">Пропустить</button>
                    <button class="btn btn-sm btn-primary" id="onboarding-next">
                        ${isLast ? 'Готово' : 'Далее'} →
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.tooltip);
        
        // Позиционирование
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        
        if (step.position === 'bottom') {
            this.tooltip.style.top = `${rect.bottom + 10}px`;
            this.tooltip.style.left = `${rect.left + (rect.width - tooltipRect.width) / 2}px`;
        } else {
            this.tooltip.style.top = `${rect.top - tooltipRect.height - 10}px`;
            this.tooltip.style.left = `${rect.left + (rect.width - tooltipRect.width) / 2}px`;
        }
        
        // События
        document.getElementById('onboarding-next').addEventListener('click', () => {
            this.showStep(index + 1);
        });
        
        document.getElementById('onboarding-skip').addEventListener('click', () => {
            this.complete();
        });
        
        // Скролл к элементу
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    complete() {
        // Убираем оверлей и тултип
        if (this.overlay) this.overlay.remove();
        if (this.tooltip) this.tooltip.remove();
        
        // Убираем выделение
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
        
        // Сохраняем что прошли онбординг
        localStorage.setItem('onboarding_completed', 'true');
    }
}

// Функция для запуска онбординга вручную
function startOnboarding() {
    localStorage.removeItem('onboarding_completed');
    new Onboarding();
}

// Auto-init для новых пользователей
if (document.querySelector('[data-user-registered]')) {
    new Onboarding();
}

