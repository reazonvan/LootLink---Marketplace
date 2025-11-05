# Deploy to production server
$server = "root@91.218.245.178"

Write-Host "Deploying to production server..." -ForegroundColor Cyan
Write-Host ""

ssh $server @"
cd /opt/lootlink
echo 'Step 1: Pulling code...'
git fetch origin
git reset --hard origin/main

echo 'Step 2: Installing dependencies...'
source venv/bin/activate
pip install -r requirements.txt

echo 'Step 3: Running migrations...'
python manage.py migrate

echo 'Step 4: Creating filters...'
python manage.py create_default_filters || echo 'Filters command executed'

echo 'Step 5: Creating demo content...'
python manage.py create_demo_listings --count=30 || echo 'Demo command executed'

echo 'Step 6: Collecting static...'
python manage.py collectstatic --noinput

echo 'Step 7: Restarting services...'
sudo systemctl restart lootlink
sudo systemctl reload nginx

echo 'Step 8: Checking status...'
sudo systemctl status lootlink --no-pager | head -10

echo ''
echo 'DONE! Check http://91.218.245.178'
"@

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green

