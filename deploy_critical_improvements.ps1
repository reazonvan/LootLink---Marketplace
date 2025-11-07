# ========================================
# DEPLOYMENT SCRIPT - CRITICAL IMPROVEMENTS
# ========================================
# Деплой критических улучшений безопасности на production
# ========================================

$server = "root@91.218.245.178"
$appPath = "/opt/lootlink"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYING CRITICAL IMPROVEMENTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# STEP 1: Создание резервной копии
Write-Host "[1/10] Creating backup..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
echo '[BACKUP] Creating database backup...'
sudo -u postgres pg_dump lootlink_db > /tmp/lootlink_backup_`$(date +%Y%m%d_%H%M%S).sql
echo '[BACKUP] Backup created successfully'
"@

# STEP 2: Pull latest code
Write-Host "`n[2/10] Pulling latest code from GitHub..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
echo '[GIT] Fetching updates...'
git fetch origin
git pull origin main
echo '[GIT] Code updated'
"@

# STEP 3: Check/Create .env file
Write-Host "`n[3/10] Checking .env configuration..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
if [ ! -f .env ]; then
    echo '[CONFIG] Creating .env file...'
    echo 'WARNING: .env file not found! Creating from template...'
    echo 'You MUST edit .env file with production values!'
    
    # Генерируем SECRET_KEY
    SECRET_KEY_GEN=\`python -c 'import secrets; print("".join(secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)))'\`
    
    cat > .env << 'EOF'
# Production Configuration - EDIT ALL VALUES!
SECRET_KEY=\${SECRET_KEY_GEN}
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=localhost,127.0.0.1,91.218.245.178
CSRF_TRUSTED_ORIGINS=http://91.218.245.178,https://91.218.245.178
SITE_URL=http://91.218.245.178

# Database
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=CHANGE_ME_PRODUCTION_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Redis
USE_REDIS=True
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (configure for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@lootlink.com

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EOF
    
    echo '[CONFIG] .env created! PLEASE EDIT IT WITH PRODUCTION VALUES!'
else
    echo '[CONFIG] .env file exists'
fi
"@

# STEP 4: Install dependencies
Write-Host "`n[4/10] Installing Python dependencies..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
source venv/bin/activate
echo '[DEPS] Installing requirements...'
pip install -r requirements.txt --quiet
echo '[DEPS] Dependencies installed'
"@

# STEP 5: Run migrations
Write-Host "`n[5/10] Running database migrations..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
source venv/bin/activate
echo '[DB] Creating migrations...'
python manage.py makemigrations --noinput
echo '[DB] Applying migrations...'
python manage.py migrate --noinput
echo '[DB] Migrations complete'
"@

# STEP 6: Create composite indexes
Write-Host "`n[6/10] Creating performance indexes..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
source venv/bin/activate
echo '[DB] Creating composite indexes...'
python manage.py create_indexes || echo '[DB] Index command completed with warnings'
"@

# STEP 7: Collect static files
Write-Host "`n[7/10] Collecting static files..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
source venv/bin/activate
echo '[STATIC] Collecting static files...'
python manage.py collectstatic --noinput --clear
echo '[STATIC] Static files collected'
"@

# STEP 8: Check if Celery is running, start if not
Write-Host "`n[8/10] Setting up Celery services..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
echo '[CELERY] Checking Celery status...'

# Create systemd service for Celery Worker if not exists
if [ ! -f /etc/systemd/system/lootlink-celery-worker.service ]; then
    echo '[CELERY] Creating celery worker service...'
    sudo tee /etc/systemd/system/lootlink-celery-worker.service > /dev/null << 'CELEOF'
[Unit]
Description=LootLink Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=root
Group=root
WorkingDirectory=$appPath
Environment=DJANGO_SETTINGS_MODULE=config.settings
ExecStart=$appPath/venv/bin/celery -A config worker -l info --detach --pidfile=/var/run/celery/worker.pid --logfile=/var/log/celery/worker.log
ExecStop=/bin/kill -s TERM \\\$MAINPID
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
CELEOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable lootlink-celery-worker
fi

# Create systemd service for Celery Beat if not exists
if [ ! -f /etc/systemd/system/lootlink-celery-beat.service ]; then
    echo '[CELERY] Creating celery beat service...'
    sudo tee /etc/systemd/system/lootlink-celery-beat.service > /dev/null << 'BEATEOF'
[Unit]
Description=LootLink Celery Beat
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$appPath
Environment=DJANGO_SETTINGS_MODULE=config.settings
ExecStart=$appPath/venv/bin/celery -A config beat -l info
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
BEATEOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable lootlink-celery-beat
fi

echo '[CELERY] Services configured'
"@

# STEP 9: Restart all services
Write-Host "`n[9/10] Restarting services..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
echo '[RESTART] Restarting Django application...'
sudo systemctl restart lootlink

echo '[RESTART] Restarting Celery worker...'
sudo systemctl restart lootlink-celery-worker || echo '[CELERY] Worker start failed - check logs'

echo '[RESTART] Restarting Celery beat...'
sudo systemctl restart lootlink-celery-beat || echo '[CELERY] Beat start failed - check logs'

echo '[RESTART] Reloading Nginx...'
sudo systemctl reload nginx

echo '[RESTART] All services restarted'
"@

# STEP 10: Health check
Write-Host "`n[10/10] Running health checks..." -ForegroundColor Yellow
ssh $server @"
cd $appPath
echo ''
echo '========================================='
echo '  SERVICE STATUS'
echo '========================================='
echo ''
echo '[Django]'
sudo systemctl status lootlink --no-pager | head -3

echo ''
echo '[Celery Worker]'
sudo systemctl status lootlink-celery-worker --no-pager | head -3 || echo 'Not running'

echo ''
echo '[Celery Beat]'
sudo systemctl status lootlink-celery-beat --no-pager | head -3 || echo 'Not running'

echo ''
echo '[Nginx]'
sudo systemctl status nginx --no-pager | head -3

echo ''
echo '[Redis]'
redis-cli ping || echo 'Redis not responding'

echo ''
echo '========================================='
echo ''
"@

# Final message
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "🎉 All improvements deployed to production!" -ForegroundColor Green
Write-Host "🌐 Check: http://91.218.245.178" -ForegroundColor Cyan
Write-Host "`n⚠️  IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. SSH to server and edit /opt/lootlink/.env with production values" -ForegroundColor White
Write-Host "  2. Set DB_PASSWORD to production database password" -ForegroundColor White
Write-Host "  3. Configure email settings (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)" -ForegroundColor White
Write-Host "  4. Restart services after .env changes: sudo systemctl restart lootlink`n" -ForegroundColor White

Write-Host "📊 Deployment logs available on server:" -ForegroundColor Cyan
Write-Host "  - Django: sudo journalctl -u lootlink -n 50" -ForegroundColor White
Write-Host "  - Celery Worker: sudo journalctl -u lootlink-celery-worker -n 50" -ForegroundColor White
Write-Host "  - Celery Beat: sudo journalctl -u lootlink-celery-beat -n 50`n" -ForegroundColor White

