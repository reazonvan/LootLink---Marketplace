/**
 * Динамическая загрузка категорий при выборе игры
 */

document.addEventListener('DOMContentLoaded', function() {
    const gameSelect = document.getElementById('id_game');
    const categorySelect = document.getElementById('id_category');
    
    if (!gameSelect || !categorySelect) {
        return; // Нет нужных полей на странице
    }
    
    console.log('🎮 Category selector initialized');
    
    // Функция загрузки категорий
    function loadCategories(gameId) {
        if (!gameId) {
            categorySelect.innerHTML = '<option value="">---------</option>';
            categorySelect.disabled = true;
            return;
        }
        
        // Показываем loading
        categorySelect.disabled = true;
        categorySelect.innerHTML = '<option value="">Загрузка...</option>';
        
        // Получаем CSRF токен
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // AJAX запрос для получения категорий
        fetch(`/api/categories/?game=${gameId}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Очищаем select
            categorySelect.innerHTML = '<option value="">Не выбрано (необязательно)</option>';
            
            // Добавляем категории
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                if (category.icon) {
                    option.textContent = `${category.name}`;
                }
                categorySelect.appendChild(option);
            });
            
            categorySelect.disabled = false;
            console.log(`✅ Загружено ${data.categories.length} категорий`);
        })
        .catch(error => {
            console.error('❌ Ошибка загрузки категорий:', error);
            categorySelect.innerHTML = '<option value="">Ошибка загрузки</option>';
            categorySelect.disabled = false;
        });
    }
    
    // При изменении игры - загружаем категории
    gameSelect.addEventListener('change', function() {
        const gameId = this.value;
        loadCategories(gameId);
    });
    
    // Если игра уже выбрана при загрузке страницы - загружаем категории
    if (gameSelect.value) {
        loadCategories(gameSelect.value);
    }
});

