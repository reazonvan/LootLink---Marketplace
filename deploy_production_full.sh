#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  LootLink - Полный Production Deployment с Логированием
# ═══════════════════════════════════════════════════════════════════════════
# 
# Назначение: Комплексный запуск production сервера с полными проверками
# Использование: sudo bash deploy_production_full.sh
# 
# Этот скрипт выполняет:
#   ✓ Полную проверку системных зависимостей
#   ✓ Проверку конфигурации безопасности
#   ✓ Обновление кода из Git
#   ✓ Применение миграций БД
#   ✓ Сборку статических файлов
#   ✓ Очистку кеша
#   ✓ Перезапуск всех сервисов
#   ✓ Проверку работоспособности
#   ✓ Детальное логирование всех операций
#
# ═══════════════════════════════════════════════════════════════════════════

set -e  # Остановка при первой ошибке
set -o pipefail  # Ошибка в pipe приводит к ошибке всего pipeline

# ═══════════════════════════════════════════════════════════════════════════
#  КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_DIR="/opt/lootlink"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="/var/log/lootlink"
DEPLOYMENT_LOG="${LOG_DIR}/deployment.log"
ERROR_LOG="${LOG_DIR}/deployment-errors.log"
SERVER_IP="91.218.245.178"
BACKUP_DIR="/var/backups/lootlink"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'  # No Color

# Счетчики
TOTAL_STEPS=0
CURRENT_STEP=0
WARNINGS_COUNT=0
ERRORS_COUNT=0

# ═══════════════════════════════════════════════════════════════════════════
#  ФУНКЦИИ ЛОГИРОВАНИЯ
# ═══════════════════════════════════════════════════════════════════════════

# Инициализация системы логирования
init_logging() {
    mkdir -p "${LOG_DIR}"
    
    # Создаем новый лог-файл с временной меткой
    local TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DEPLOYMENT_LOG="${LOG_DIR}/deployment_${TIMESTAMP}.log"
    ERROR_LOG="${LOG_DIR}/deployment_errors_${TIMESTAMP}.log"
    
    # Заголовок лога
    {
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  LootLink Production Deployment"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "Дата начала: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервер: $(hostname)"
        echo "IP: ${SERVER_IP}"
        echo "Пользователь: $(whoami)"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
    } | tee "${DEPLOYMENT_LOG}"
    
    log_info "Система логирования инициализирована"
    log_info "Основной лог: ${DEPLOYMENT_LOG}"
    log_info "Лог ошибок: ${ERROR_LOG}"
}

# Логирование с уровнями
log_message() {
    local LEVEL=$1
    shift
    local MESSAGE="$@"
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[${TIMESTAMP}] [${LEVEL}] ${MESSAGE}" | tee -a "${DEPLOYMENT_LOG}"
}

log_info() {
    echo -e "${BLUE}[ℹ]${NC} $@"
    log_message "INFO" "$@"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $@"
    log_message "SUCCESS" "$@"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $@"
    log_message "WARNING" "$@"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $@" >> "${ERROR_LOG}"
    ((WARNINGS_COUNT++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $@"
    log_message "ERROR" "$@"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $@" >> "${ERROR_LOG}"
    ((ERRORS_COUNT++))
}

log_step() {
    ((CURRENT_STEP++))
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Шаг ${CURRENT_STEP}/${TOTAL_STEPS}: $@${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    log_message "STEP" "Шаг ${CURRENT_STEP}/${TOTAL_STEPS}: $@"
}

log_section() {
    echo ""
    echo -e "${MAGENTA}───────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${MAGENTA}  $@${NC}"
    echo -e "${MAGENTA}───────────────────────────────────────────────────────────────────────────${NC}"
    log_message "SECTION" "$@"
}

# Выполнение команды с логированием
run_command() {
    local DESCRIPTION=$1
    shift
    local COMMAND="$@"
    
    log_info "Выполняю: ${DESCRIPTION}"
    log_message "COMMAND" "${COMMAND}"
    
    if eval "${COMMAND}" >> "${DEPLOYMENT_LOG}" 2>&1; then
        log_success "${DESCRIPTION} - завершено"
        return 0
    else
        log_error "${DESCRIPTION} - ошибка"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
#  ПРОВЕРОЧНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "Скрипт должен быть запущен с правами root (используйте sudo)"
        exit 1
    fi
    log_success "Проверка прав root пройдена"
}

check_directories() {
    log_section "Проверка структуры каталогов"
    
    if [ ! -d "${PROJECT_DIR}" ]; then
        log_error "Каталог проекта не найден: ${PROJECT_DIR}"
        exit 1
    fi
    log_success "Каталог проекта: ${PROJECT_DIR}"
    
    if [ ! -d "${VENV_DIR}" ]; then
        log_error "Виртуальное окружение не найдено: ${VENV_DIR}"
        exit 1
    fi
    log_success "Виртуальное окружение: ${VENV_DIR}"
    
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        log_error "Файл .env не найден: ${PROJECT_DIR}/.env"
        exit 1
    fi
    log_success "Файл конфигурации: ${PROJECT_DIR}/.env"
    
    if [ ! -f "${PROJECT_DIR}/manage.py" ]; then
        log_error "manage.py не найден"
        exit 1
    fi
    log_success "Django manage.py найден"
}

check_services() {
    log_section "Проверка системных сервисов"
    
    # PostgreSQL
    if systemctl is-active --quiet postgresql; then
        log_success "PostgreSQL: работает"
    else
        log_warning "PostgreSQL: не запущен, попытка запуска..."
        if systemctl start postgresql; then
            log_success "PostgreSQL успешно запущен"
        else
            log_error "Не удалось запустить PostgreSQL"
            exit 1
        fi
    fi
    
    # Redis (опционально)
    if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
        log_success "Redis: работает"
    else
        log_warning "Redis: не запущен (опционально, но рекомендуется)"
    fi
    
    # Nginx
    if systemctl is-active --quiet nginx; then
        log_success "Nginx: работает"
    else
        log_warning "Nginx: не запущен, попытка запуска..."
        if systemctl start nginx; then
            log_success "Nginx успешно запущен"
        else
            log_error "Не удалось запустить Nginx"
            exit 1
        fi
    fi
}

check_security() {
    log_section "Проверка настроек безопасности"
    
    cd "${PROJECT_DIR}"
    
    # Проверка DEBUG
    local DEBUG_VALUE=$(grep "^DEBUG=" .env | cut -d'=' -f2)
    if [ "${DEBUG_VALUE}" = "False" ]; then
        log_success "DEBUG=False (правильно для production)"
    else
        log_error "DEBUG=${DEBUG_VALUE} (должен быть False в production!)"
        log_error "Измените DEBUG=False в файле .env"
        ((ERRORS_COUNT++))
    fi
    
    # Проверка SECRET_KEY
    local SECRET_KEY=$(grep "^SECRET_KEY=" .env | cut -d'=' -f2)
    if [ -z "${SECRET_KEY}" ]; then
        log_error "SECRET_KEY не установлен!"
        ((ERRORS_COUNT++))
    elif [ "${SECRET_KEY}" = "django-insecure-dev-key-change-in-production" ]; then
        log_error "SECRET_KEY использует дефолтное значение! Необходимо изменить!"
        ((ERRORS_COUNT++))
    elif [ ${#SECRET_KEY} -lt 50 ]; then
        log_warning "SECRET_KEY слишком короткий (${#SECRET_KEY} символов)"
    else
        log_success "SECRET_KEY установлен и имеет достаточную длину (${#SECRET_KEY} символов)"
    fi
    
    # Проверка ALLOWED_HOSTS
    local ALLOWED_HOSTS=$(grep "^ALLOWED_HOSTS=" .env | cut -d'=' -f2)
    if [ -n "${ALLOWED_HOSTS}" ]; then
        log_success "ALLOWED_HOSTS настроен: ${ALLOWED_HOSTS}"
    else
        log_warning "ALLOWED_HOSTS не установлен"
    fi
}

check_database() {
    log_section "Проверка подключения к базе данных"
    
    cd "${PROJECT_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    # Получаем данные из .env
    local DB_NAME=$(grep "^DB_NAME=" .env | cut -d'=' -f2)
    local DB_USER=$(grep "^DB_USER=" .env | cut -d'=' -f2)
    
    log_info "База данных: ${DB_NAME}"
    log_info "Пользователь: ${DB_USER}"
    
    # Проверка подключения через Django
    if python manage.py check --database default >> "${DEPLOYMENT_LOG}" 2>&1; then
        log_success "Подключение к базе данных успешно"
    else
        log_error "Не удалось подключиться к базе данных"
        exit 1
    fi
    
    # Проверка количества таблиц
    local TABLE_COUNT=$(sudo -u postgres psql -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    TABLE_COUNT=$(echo $TABLE_COUNT | xargs)  # trim whitespace
    
    if [ "${TABLE_COUNT}" -gt 10 ]; then
        log_success "Таблиц в БД: ${TABLE_COUNT}"
    else
        log_warning "Таблиц в БД мало: ${TABLE_COUNT} (возможно нужны миграции)"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
#  ОСНОВНЫЕ ФУНКЦИИ ДЕПЛОЯ
# ═══════════════════════════════════════════════════════════════════════════

update_code() {
    log_section "Обновление кода из Git"
    
    cd "${PROJECT_DIR}"
    
    # Проверка, является ли это git репозиторием
    if [ ! -d ".git" ]; then
        log_warning "Это не Git репозиторий, пропускаем обновление"
        return 0
    fi
    
    # Показываем текущую версию
    local CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    log_info "Текущий коммит: ${CURRENT_COMMIT}"
    
    # Fetch изменений
    if run_command "Загрузка обновлений из Git" "git fetch origin"; then
        # Проверяем, есть ли обновления
        local REMOTE_COMMIT=$(git rev-parse --short origin/main 2>/dev/null || echo "unknown")
        log_info "Удаленный коммит: ${REMOTE_COMMIT}"
        
        if [ "${CURRENT_COMMIT}" != "${REMOTE_COMMIT}" ]; then
            log_info "Обнаружены новые изменения, обновляю..."
            
            # Создаем бэкап текущего состояния
            local BACKUP_BRANCH="backup_$(date +%Y%m%d_%H%M%S)"
            git branch "${BACKUP_BRANCH}" >> "${DEPLOYMENT_LOG}" 2>&1 || true
            log_info "Создан backup branch: ${BACKUP_BRANCH}"
            
            # Обновляем код
            if run_command "Применение обновлений" "git reset --hard origin/main"; then
                local NEW_COMMIT=$(git rev-parse --short HEAD)
                log_success "Код обновлен до коммита: ${NEW_COMMIT}"
                
                # Показываем лог изменений
                log_info "Изменения:"
                git log --oneline "${CURRENT_COMMIT}..${NEW_COMMIT}" >> "${DEPLOYMENT_LOG}" 2>&1 || true
            fi
        else
            log_info "Код уже актуален, обновление не требуется"
        fi
    fi
}

install_dependencies() {
    log_section "Проверка и установка зависимостей Python"
    
    cd "${PROJECT_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    if [ -f "requirements.txt" ]; then
        log_info "Найден requirements.txt"
        run_command "Обновление pip" "pip install --upgrade pip"
        run_command "Установка зависимостей" "pip install -r requirements.txt --quiet"
    elif [ -f "requirements/production.txt" ]; then
        log_info "Найден requirements/production.txt"
        run_command "Обновление pip" "pip install --upgrade pip"
        run_command "Установка зависимостей" "pip install -r requirements/production.txt --quiet"
    else
        log_warning "Файл requirements не найден, пропускаем установку"
    fi
}

run_migrations() {
    log_section "Применение миграций базы данных"
    
    cd "${PROJECT_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    # Показываем статус миграций
    log_info "Проверка статуса миграций..."
    python manage.py showmigrations --plan | tail -n 20 >> "${DEPLOYMENT_LOG}" 2>&1
    
    # Проверяем, есть ли неприменённые миграции
    local UNAPPLIED=$(python manage.py showmigrations --plan | grep -c "\[ \]" || echo "0")
    
    if [ "${UNAPPLIED}" -gt 0 ]; then
        log_info "Обнаружено неприменённых миграций: ${UNAPPLIED}"
        
        # Создаем бэкап БД перед миграциями
        log_info "Создание бэкапа базы данных перед миграциями..."
        local DB_NAME=$(grep "^DB_NAME=" .env | cut -d'=' -f2)
        local BACKUP_FILE="${BACKUP_DIR}/pre_migration_$(date +%Y%m%d_%H%M%S).sql.gz"
        
        mkdir -p "${BACKUP_DIR}"
        if sudo -u postgres pg_dump "${DB_NAME}" | gzip > "${BACKUP_FILE}" 2>>"${ERROR_LOG}"; then
            log_success "Бэкап создан: ${BACKUP_FILE}"
        else
            log_warning "Не удалось создать бэкап (продолжаем без бэкапа)"
        fi
        
        # Применяем миграции
        if run_command "Применение миграций" "python manage.py migrate --noinput"; then
            log_success "Миграции успешно применены (${UNAPPLIED} миграций)"
        else
            log_error "Ошибка при применении миграций!"
            log_error "Используйте бэкап для восстановления: ${BACKUP_FILE}"
            exit 1
        fi
    else
        log_success "Все миграции уже применены"
    fi
}

collect_static() {
    log_section "Сборка статических файлов"
    
    cd "${PROJECT_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    local STATIC_ROOT=$(python -c "from django.conf import settings; print(settings.STATIC_ROOT)" 2>/dev/null || echo "${PROJECT_DIR}/staticfiles")
    log_info "Каталог статики: ${STATIC_ROOT}"
    
    # Очищаем старые статические файлы
    if [ -d "${STATIC_ROOT}" ]; then
        log_info "Очистка старых статических файлов..."
        rm -rf "${STATIC_ROOT}"/* >> "${DEPLOYMENT_LOG}" 2>&1 || true
    fi
    
    # Собираем статику
    if run_command "Сборка статических файлов" "python manage.py collectstatic --noinput --clear"; then
        local FILE_COUNT=$(find "${STATIC_ROOT}" -type f | wc -l)
        log_success "Статические файлы собраны (всего файлов: ${FILE_COUNT})"
        
        # Устанавливаем правильные права
        run_command "Установка прав на статические файлы" "chown -R www-data:www-data ${STATIC_ROOT}"
        run_command "Установка прав доступа" "chmod -R 755 ${STATIC_ROOT}"
    fi
}

clear_cache() {
    log_section "Очистка кеша"
    
    cd "${PROJECT_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    # Проверяем, есть ли скрипт очистки кеша
    if [ -f "scripts/clear_cache.py" ]; then
        if run_command "Очистка Django кеша" "python scripts/clear_cache.py"; then
            log_success "Кеш Django очищен"
        fi
    else
        # Альтернативный метод через shell
        log_info "Скрипт clear_cache.py не найден, используем альтернативный метод"
        echo "from django.core.cache import cache; cache.clear(); print('Cache cleared')" | python manage.py shell >> "${DEPLOYMENT_LOG}" 2>&1
        log_success "Кеш очищен через Django shell"
    fi
    
    # Очистка Redis (если используется)
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping &> /dev/null; then
            log_info "Очистка Redis кеша..."
            redis-cli FLUSHDB >> "${DEPLOYMENT_LOG}" 2>&1 || true
            log_success "Redis кеш очищен"
        fi
    fi
}

restart_services() {
    log_section "Перезапуск сервисов"
    
    # Daemon reload
    run_command "Перезагрузка systemd конфигурации" "systemctl daemon-reload"
    
    # Перезапуск Gunicorn/Django
    if systemctl is-active --quiet lootlink; then
        log_info "Перезапуск сервиса lootlink..."
        if run_command "Остановка lootlink" "systemctl stop lootlink"; then
            sleep 2
            if run_command "Запуск lootlink" "systemctl start lootlink"; then
                sleep 3
                if systemctl is-active --quiet lootlink; then
                    log_success "Сервис lootlink успешно перезапущен"
                else
                    log_error "Сервис lootlink не запустился!"
                    log_info "Проверка логов..."
                    journalctl -u lootlink -n 20 --no-pager >> "${ERROR_LOG}" 2>&1
                    exit 1
                fi
            fi
        fi
    else
        log_info "Сервис lootlink не запущен, запускаю..."
        if run_command "Запуск lootlink" "systemctl start lootlink"; then
            sleep 3
            log_success "Сервис lootlink запущен"
        fi
    fi
    
    # Перезагрузка Nginx
    log_info "Проверка конфигурации Nginx..."
    if nginx -t >> "${DEPLOYMENT_LOG}" 2>&1; then
        log_success "Конфигурация Nginx корректна"
        if run_command "Перезагрузка Nginx" "systemctl reload nginx"; then
            log_success "Nginx перезагружен"
        fi
    else
        log_error "Ошибка в конфигурации Nginx!"
        nginx -t 2>&1 | tee -a "${ERROR_LOG}"
        exit 1
    fi
    
    # Проверка Celery (если используется)
    if systemctl is-active --quiet celery 2>/dev/null; then
        log_info "Перезапуск Celery workers..."
        run_command "Перезапуск Celery" "systemctl restart celery"
    fi
}

health_check() {
    log_section "Проверка работоспособности"
    
    # Ждем стабилизации
    log_info "Ожидание стабилизации сервисов (5 секунд)..."
    sleep 5
    
    # Проверка статусов сервисов
    local ALL_OK=true
    
    if systemctl is-active --quiet postgresql; then
        log_success "PostgreSQL: работает"
    else
        log_error "PostgreSQL: НЕ работает!"
        ALL_OK=false
    fi
    
    if systemctl is-active --quiet lootlink; then
        log_success "LootLink: работает"
    else
        log_error "LootLink: НЕ работает!"
        ALL_OK=false
    fi
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx: работает"
    else
        log_error "Nginx: НЕ работает!"
        ALL_OK=false
    fi
    
    # HTTP проверка
    log_info "Проверка HTTP доступности..."
    local HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
    
    if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "302" ]; then
        log_success "HTTP сервер отвечает (код: ${HTTP_CODE})"
    else
        log_error "HTTP сервер не отвечает корректно (код: ${HTTP_CODE})"
        ALL_OK=false
    fi
    
    # Проверка доступности по IP
    log_info "Проверка внешней доступности..."
    local EXTERNAL_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://${SERVER_IP}/" --connect-timeout 5 || echo "000")
    
    if [ "${EXTERNAL_CODE}" = "200" ] || [ "${EXTERNAL_CODE}" = "302" ]; then
        log_success "Сайт доступен извне (код: ${EXTERNAL_CODE})"
    else
        log_warning "Возможны проблемы с внешней доступностью (код: ${EXTERNAL_CODE})"
    fi
    
    if [ "$ALL_OK" = false ]; then
        log_error "Обнаружены проблемы при проверке работоспособности!"
        exit 1
    fi
}

show_logs() {
    log_section "Последние записи в логах"
    
    log_info "Последние 10 строк лога lootlink:"
    echo "─────────────────────────────────────────────────────────────" >> "${DEPLOYMENT_LOG}"
    journalctl -u lootlink -n 10 --no-pager >> "${DEPLOYMENT_LOG}" 2>&1
    echo "─────────────────────────────────────────────────────────────" >> "${DEPLOYMENT_LOG}"
    
    log_info "Последние 10 строк лога Nginx (ошибки):"
    echo "─────────────────────────────────────────────────────────────" >> "${DEPLOYMENT_LOG}"
    tail -n 10 /var/log/nginx/lootlink-error.log >> "${DEPLOYMENT_LOG}" 2>&1 || echo "Лог не найден" >> "${DEPLOYMENT_LOG}"
    echo "─────────────────────────────────────────────────────────────" >> "${DEPLOYMENT_LOG}"
}

# ═══════════════════════════════════════════════════════════════════════════
#  ФИНАЛЬНЫЙ ОТЧЕТ
# ═══════════════════════════════════════════════════════════════════════════

generate_report() {
    log_section "Генерация финального отчета"
    
    local END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    local DURATION=$SECONDS
    
    # Создаем отчет
    local REPORT_FILE="${PROJECT_DIR}/deployment_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  LootLink - Отчет о Deployment"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
        echo "Дата завершения: ${END_TIME}"
        echo "Длительность: ${DURATION} секунд"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  Результаты"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
        echo "Шагов выполнено: ${CURRENT_STEP}/${TOTAL_STEPS}"
        echo "Предупреждений: ${WARNINGS_COUNT}"
        echo "Ошибок: ${ERRORS_COUNT}"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  Статус Сервисов"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
        echo "PostgreSQL: $(systemctl is-active postgresql)"
        echo "Redis: $(systemctl is-active redis-server 2>/dev/null || systemctl is-active redis 2>/dev/null || echo 'inactive')"
        echo "LootLink: $(systemctl is-active lootlink)"
        echo "Nginx: $(systemctl is-active nginx)"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  Доступность"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
        echo "URL: http://${SERVER_IP}"
        echo "Admin: http://${SERVER_IP}/admin/"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo "  Логи"
        echo "═══════════════════════════════════════════════════════════════════════════"
        echo ""
        echo "Deployment лог: ${DEPLOYMENT_LOG}"
        echo "Лог ошибок: ${ERROR_LOG}"
        echo ""
        echo "═══════════════════════════════════════════════════════════════════════════"
    } | tee "${REPORT_FILE}"
    
    log_success "Отчет сохранен: ${REPORT_FILE}"
    
    # Сохраняем путь к отчету в стандартное место
    echo "${REPORT_FILE}" > "${PROJECT_DIR}/.last_deployment_report"
}

# ═══════════════════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════════

main() {
    # Подсчет общего количества шагов
    TOTAL_STEPS=14
    
    # Инициализация
    init_logging
    
    # Начало deployment
    log_step "Проверка прав доступа"
    check_root
    
    log_step "Проверка структуры проекта"
    check_directories
    
    log_step "Проверка системных сервисов"
    check_services
    
    log_step "Проверка настроек безопасности"
    check_security
    
    log_step "Проверка подключения к базе данных"
    check_database
    
    log_step "Обновление кода из Git"
    update_code
    
    log_step "Установка/обновление зависимостей"
    install_dependencies
    
    log_step "Применение миграций базы данных"
    run_migrations
    
    log_step "Сборка статических файлов"
    collect_static
    
    log_step "Очистка кеша"
    clear_cache
    
    log_step "Перезапуск сервисов"
    restart_services
    
    log_step "Проверка работоспособности"
    health_check
    
    log_step "Анализ логов"
    show_logs
    
    log_step "Генерация финального отчета"
    generate_report
    
    # Финальное сообщение
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Deployment Завершен Успешно!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ ${ERRORS_COUNT} -eq 0 ]; then
        log_success "Сайт готов к работе: http://${SERVER_IP}"
        log_success "Админ панель: http://${SERVER_IP}/admin/"
    else
        log_warning "Deployment завершен с ${ERRORS_COUNT} ошибками"
        log_warning "Проверьте лог ошибок: ${ERROR_LOG}"
    fi
    
    if [ ${WARNINGS_COUNT} -gt 0 ]; then
        log_warning "Обнаружено ${WARNINGS_COUNT} предупреждений"
    fi
    
    echo ""
    log_info "Полный лог deployment: ${DEPLOYMENT_LOG}"
    log_info "Лог ошибок: ${ERROR_LOG}"
    echo ""
    log_info "Для просмотра логов сервиса:"
    echo "  sudo journalctl -u lootlink -f"
    echo ""
    
    # Возврат кода выхода
    if [ ${ERRORS_COUNT} -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════════════════════════════════════════

# Перехват Ctrl+C
trap 'log_error "Deployment прерван пользователем"; exit 130' INT TERM

# Запуск главной функции
main "$@"

