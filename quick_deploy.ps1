# Quick deploy script for LootLink
$server = "root@91.218.245.178"

Write-Host "Deploying to production..." -ForegroundColor Cyan

# Git pull
Write-Host "Step 1: Pulling code..." -ForegroundColor Yellow
ssh $server "cd /opt/lootlink && git pull origin main"

# Install dependencies
Write-Host "Step 2: Installing dependencies..." -ForegroundColor Yellow
ssh $server "cd /opt/lootlink && source venv/bin/activate && pip install -r requirements.txt"

# Migrations
Write-Host "Step 3: Running migrations..." -ForegroundColor Yellow
ssh $server "cd /opt/lootlink && source venv/bin/activate && python manage.py migrate"

# Collect static
Write-Host "Step 4: Collecting static..." -ForegroundColor Yellow
ssh $server "cd /opt/lootlink && source venv/bin/activate && python manage.py collectstatic --noinput"

# Restart services
Write-Host "Step 5: Restarting services..." -ForegroundColor Yellow
ssh $server "sudo systemctl restart lootlink && sudo systemctl reload nginx"

Write-Host ""
Write-Host "Deploy complete! Check http://91.218.245.178" -ForegroundColor Green

