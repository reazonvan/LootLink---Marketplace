# Обновление production сервера
$server = "root@91.218.245.178"

Write-Host "Обновляю production сервер..." -ForegroundColor Cyan

ssh $server @"
cd /opt/lootlink
git pull origin main
source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart lootlink nginx
echo 'Готово!'
"@

Write-Host "Сервер обновлен! Проверяйте сайт." -ForegroundColor Green

