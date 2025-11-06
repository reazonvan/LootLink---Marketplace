# ==========================================
# Setup HTTPS on Production Server
# ==========================================

$ErrorActionPreference = "Stop"
$server = "root@91.218.245.178"

Write-Host "Setting up HTTPS on production server..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Upload scripts
Write-Host "Step 1: Uploading scripts to server..." -ForegroundColor Yellow
scp scripts/setup_https.sh ${server}:/tmp/
scp scripts/enable_django_https.sh ${server}:/tmp/
Write-Host "Scripts uploaded successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Make scripts executable and run HTTPS setup
Write-Host "Step 2: Installing SSL certificate..." -ForegroundColor Yellow
ssh $server @"
chmod +x /tmp/setup_https.sh
chmod +x /tmp/enable_django_https.sh
/tmp/setup_https.sh
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: SSL setup failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Enable Django HTTPS settings
Write-Host "Step 3: Updating Django settings..." -ForegroundColor Yellow
ssh $server "/tmp/enable_django_https.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Django settings update failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "HTTPS successfully configured!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Site is now available at:" -ForegroundColor Cyan
Write-Host "   https://91.218.245.178" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "   Using self-signed certificate" -ForegroundColor White
Write-Host "   Browser will show security warning" -ForegroundColor White
Write-Host "   This is normal for IP address without domain" -ForegroundColor White
Write-Host ""
Write-Host "To remove warning:" -ForegroundColor Yellow
Write-Host "   1. Buy domain name (e.g. lootlink.ru)" -ForegroundColor White
Write-Host "   2. Configure DNS A-record to 91.218.245.178" -ForegroundColor White
Write-Host "   3. Install Let's Encrypt certificate" -ForegroundColor White
Write-Host ""
Write-Host "Testing site..." -ForegroundColor Cyan

# Test HTTPS connection
try {
    Write-Host "   Testing HTTPS connection..."
    $response = Invoke-WebRequest -Uri "https://91.218.245.178" -SkipCertificateCheck -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "   HTTPS is working!" -ForegroundColor Green
    }
} catch {
    Write-Host "   Could not verify HTTPS (might need to wait)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done! Open https://91.218.245.178 in browser" -ForegroundColor Green
Write-Host ""

