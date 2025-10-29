# Script for restarting production server
# Usage: .\restart_server.ps1

$server = "root@91.218.245.178"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  RESTART PRODUCTION SERVER" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check SSH availability
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue

if (-not $sshPath) {
    Write-Host "ERROR: SSH not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install OpenSSH:" -ForegroundColor Yellow
    Write-Host "Settings -> Apps -> Optional Features -> OpenSSH Client" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "Connecting to server $server..." -ForegroundColor Yellow
Write-Host ""

# Execute restart script on server
ssh $server "bash /opt/lootlink/scripts/restart_production.sh"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  SERVER RESTARTED!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open in browser (incognito mode):" -ForegroundColor Yellow
Write-Host "http://91.218.245.178" -ForegroundColor Cyan
Write-Host ""
