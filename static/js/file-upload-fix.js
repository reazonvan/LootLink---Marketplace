/**
 * ИСПРАВЛЕНИЕ ЗАГРУЗКИ ФАЙЛОВ - РАБОЧАЯ ВЕРСИЯ
 * Создаём кастомную кнопку которая ТОЧНО работает
 */

/**
 * Экранирование HTML для защиты от XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 File upload fix загружен');
    
    // Находим ВСЕ input type="file" на странице
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    if (fileInputs.length === 0) {
        console.log('⚠️ File inputs не найдены');
        return;
    }
    
    console.log(`✅ Найдено ${fileInputs.length} file input(s)`);
    
    fileInputs.forEach(function(input) {
        console.log('📌 Обрабатываем input:', input.id || input.name);
        
        // СКРЫВАЕМ оригинальный input
        input.style.display = 'none';
        
        // СОЗДАЁМ КАСТОМНУЮ КНОПКУ
        const customButton = document.createElement('button');
        customButton.type = 'button';
        customButton.className = 'btn btn-outline-primary w-100 custom-file-upload-btn';
        customButton.innerHTML = `
            <i class="bi bi-cloud-upload"></i> 
            <span>Выбрать ${input.id === 'id_avatar' ? 'аватар' : 'изображение'}</span>
            <small class="d-block mt-1 text-muted">Нажмите здесь для выбора файла</small>
        `;
        
        // Вставляем кнопку ПЕРЕД input
        input.parentNode.insertBefore(customButton, input);
        
        // КЛИК ПО КНОПКЕ = КЛИК ПО INPUT
        customButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🖱️ Клик по кастомной кнопке!');
            input.click();  // Триггерим клик на скрытом input
            console.log('✅ Input.click() вызван');
        });
        
        // Создаём контейнер для превью
        const previewDiv = document.createElement('div');
        previewDiv.className = 'file-preview mt-3';
        previewDiv.style.display = 'none';
        customButton.parentNode.insertBefore(previewDiv, customButton.nextSibling);
        
        // ОБРАБОТЧИК ВЫБОРА ФАЙЛА
        input.addEventListener('change', function(e) {
            console.log('📁 Файл выбран!', e.target.files[0]);
            
            const file = e.target.files[0];
            
            if (!file) {
                console.log('⚠️ Файл не выбран или отменён');
                return;
            }
            
            // Проверка типа
            if (!file.type.match('image.*')) {
                alert('❌ Пожалуйста, выберите изображение (JPG, PNG, GIF)');
                input.value = '';
                return;
            }
            
            // Проверка размера (5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('❌ Файл слишком большой! Максимум 5 МБ');
                input.value = '';
                return;
            }
            
            console.log('✅ Файл прошёл валидацию');
            
            // Показываем превью
            const reader = new FileReader();
            reader.onload = function(e) {
                console.log('🖼️ Показываем превью');
                
                // ЗАЩИТА ОТ XSS: экранируем имя файла
                const safeFileName = escapeHtml(file.name);
                const fileSizeKB = (file.size / 1024).toFixed(2);
                
                previewDiv.innerHTML = `
                    <div class="preview-container">
                        <img src="${e.target.result}" class="preview-image" alt="Preview">
                        <div class="preview-info">
                            <p class="mb-1"><strong>${safeFileName}</strong></p>
                            <p class="text-muted small mb-2">${fileSizeKB} КБ</p>
                            <button type="button" class="btn btn-sm btn-danger remove-file-btn">
                                <i class="bi bi-trash"></i> Удалить
                            </button>
                        </div>
                    </div>
                `;
                
                previewDiv.style.display = 'block';
                customButton.style.display = 'none';
                
                // Обработчик удаления
                previewDiv.querySelector('.remove-file-btn').addEventListener('click', function() {
                    console.log('🗑️ Удаление файла');
                    input.value = '';
                    previewDiv.style.display = 'none';
                    customButton.style.display = 'block';
                });
            };
            
            reader.readAsDataURL(file);
        });
        
        console.log('✅ Обработчики добавлены для', input.id || input.name);
    });
});

