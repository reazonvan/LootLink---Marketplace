# ==========================================
# Setup Let's Encrypt on Production Server
# ==========================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$false)]
    [string]$WwwDomain = ""
)

$ErrorActionPreference = "Stop"
$server = "root@91.218.245.178"

Write-Host "Setting up Let's Encrypt for $Domain..." -ForegroundColor Cyan
Write-Host ""

# Check DNS first
Write-Host "Checking DNS configuration..." -ForegroundColor Yellow
try {
    $dnsResult = Resolve-DnsName -Name $Domain -Type A -ErrorAction Stop
    $ip = $dnsResult[0].IPAddress
    Write-Host "DNS resolved: $Domain -> $ip" -ForegroundColor Green
    
    if ($ip -ne "91.218.245.178") {
        Write-Host "WARNING: DNS points to $ip, expected 91.218.245.178" -ForegroundColor Yellow
        $continue = Read-Host "Continue anyway? (y/n)"
        if ($continue -ne "y") {
            exit 1
        }
    }
} catch {
    Write-Host "ERROR: Cannot resolve DNS for $Domain" -ForegroundColor Red
    Write-Host "Please configure DNS A-record first:" -ForegroundColor Yellow
    Write-Host "  Type: A" -ForegroundColor White
    Write-Host "  Name: @" -ForegroundColor White
    Write-Host "  Value: 91.218.245.178" -ForegroundColor White
    Write-Host "  TTL: 3600" -ForegroundColor White
    exit 1
}

Write-Host ""

# Upload script
Write-Host "Uploading Let's Encrypt setup script..." -ForegroundColor Yellow
scp scripts/setup_letsencrypt.sh ${server}:/tmp/

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload script" -ForegroundColor Red
    exit 1
}

Write-Host "Script uploaded successfully" -ForegroundColor Green
Write-Host ""

# Run installation
Write-Host "Installing Let's Encrypt certificate..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Cyan
Write-Host ""

if ($WwwDomain) {
    ssh $server "chmod +x /tmp/setup_letsencrypt.sh && /tmp/setup_letsencrypt.sh $Domain $WwwDomain"
} else {
    ssh $server "chmod +x /tmp/setup_letsencrypt.sh && /tmp/setup_letsencrypt.sh $Domain"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Let's Encrypt installation failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. DNS not propagated yet (wait 5-30 minutes)" -ForegroundColor White
    Write-Host "  2. Ports 80/443 not accessible" -ForegroundColor White
    Write-Host "  3. Domain already has a certificate" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "Let's Encrypt successfully installed!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your site is now available at:" -ForegroundColor Cyan
Write-Host "  https://$Domain" -ForegroundColor White
if ($WwwDomain) {
    Write-Host "  https://$WwwDomain" -ForegroundColor White
}
Write-Host ""
Write-Host "Benefits:" -ForegroundColor Yellow
Write-Host "  - Trusted certificate (no browser warnings)" -ForegroundColor Green
Write-Host "  - Auto-renewal every 90 days" -ForegroundColor Green
Write-Host "  - Free forever" -ForegroundColor Green
Write-Host "  - HTTP/2 enabled" -ForegroundColor Green
Write-Host ""

# Test HTTPS
Write-Host "Testing HTTPS connection..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://$Domain" -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "HTTPS is working perfectly!" -ForegroundColor Green
    }
} catch {
    Write-Host "Could not verify HTTPS yet (might need a moment)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done! Open https://$Domain in browser" -ForegroundColor Green
Write-Host ""

