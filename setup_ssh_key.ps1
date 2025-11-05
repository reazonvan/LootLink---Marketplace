# Automatic SSH key setup for passwordless access
$server = "root@91.218.245.178"
$keyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Key Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if key exists
if (Test-Path $keyPath) {
    Write-Host "[OK] SSH key found" -ForegroundColor Green
    $publicKey = Get-Content $keyPath -Raw
} else {
    Write-Host "[ERROR] SSH key not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installing SSH key on server..." -ForegroundColor Yellow
Write-Host "NOTE: You need to enter password ONE TIME ONLY" -ForegroundColor Yellow
Write-Host ""

# Copy key to server - single command without &&
$result = ssh $server "mkdir -p ~/.ssh; chmod 700 ~/.ssh; echo '$publicKey' >> ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys; echo 'Key installed'"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] SSH key successfully installed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Testing passwordless connection..." -ForegroundColor Yellow
    
    # Test without password
    $testResult = ssh $server "echo 'Success! No password needed!'"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Done! No password needed anymore!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now updating production server..." -ForegroundColor Cyan
        Write-Host ""
        
        # Update server
        ssh $server "cd /opt/lootlink; git pull origin main; sudo systemctl restart lootlink; sudo systemctl reload nginx; echo 'Server updated!'"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "[OK] Server updated! Check new design!" -ForegroundColor Green
            Write-Host "URL: http://91.218.245.178/catalog/" -ForegroundColor Cyan
            Write-Host ""
        }
    }
} else {
    Write-Host "[ERROR] Failed to install key" -ForegroundColor Red
}
