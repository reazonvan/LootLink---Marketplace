#!/bin/bash
# Deploy improvements to production server

set -e

echo '════════════════════════════════════════════════════════════════'
echo '  DEPLOYING IMPROVEMENTS TO PRODUCTION'
echo '════════════════════════════════════════════════════════════════'
echo ''

cd /opt/lootlink

echo '📥 Step 1: Pulling latest code...'
git fetch origin
git reset --hard origin/main
echo '✅ Code updated'
echo ''

echo '🐍 Step 2: Activating venv and updating dependencies...'
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo '✅ Dependencies updated'
echo ''

echo '🗄️  Step 3: Applying database migrations...'
python manage.py migrate
echo '✅ Migrations applied'
echo ''

echo '🎨 Step 4: Creating default filters (FunPay-style)...'
python manage.py create_default_filters || echo 'Filters already exist or command failed'
echo ''

echo '📦 Step 5: Creating demo content (30 listings)...'
python manage.py create_demo_listings --count=30 || echo 'Demo content creation attempted'
echo ''

echo '📁 Step 6: Collecting static files...'
python manage.py collectstatic --noinput --clear
sudo chown -R www-data:www-data /opt/lootlink/staticfiles
echo '✅ Static files collected'
echo ''

echo '🔄 Step 7: Restarting services...'
sudo systemctl daemon-reload
sudo systemctl restart lootlink
sudo systemctl reload nginx
echo '✅ Services restarted'
echo ''

echo '🔍 Step 8: Checking services status...'
sudo systemctl is-active lootlink && echo '✅ LootLink is running' || echo '❌ LootLink is down!'
sudo systemctl is-active nginx && echo '✅ Nginx is running' || echo '❌ Nginx is down!'
echo ''

echo '════════════════════════════════════════════════════════════════'
echo '  ✅ DEPLOYMENT COMPLETE!'
echo '════════════════════════════════════════════════════════════════'
echo ''
echo '🌐 Site: http://91.218.245.178'
echo '📊 Check all new sections on homepage!'
echo ''

