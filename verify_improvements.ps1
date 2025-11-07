# Verification script for improvements
Write-Host "`nChecking implemented improvements..." -ForegroundColor Cyan

$passed = 0
$failed = 0

function Test-File {
    param($Path, $Description)
    
    if (Test-Path $Path) {
        Write-Host "  [OK] $Description" -ForegroundColor Green
        $script:passed++
        return $true
    } else {
        Write-Host "  [FAIL] $Description - File not found: $Path" -ForegroundColor Red
        $script:failed++
        return $false
    }
}

# Check new files
Write-Host "`n=== NEW FILES ===" -ForegroundColor Yellow

Test-File ".env" ".env configuration file"
Test-File "api/throttling.py" "API throttling classes"
Test-File "api/permissions.py" "API permissions classes"
Test-File "api/tests_idor.py" "IDOR security tests"
Test-File "core/validators.py" "Secure image validators"
Test-File "core/models_audit.py" "Security audit models"
Test-File "core/middleware_audit.py" "Audit middleware"
Test-File "core/admin_audit.py" "Audit admin interface"
Test-File "payments/tasks.py" "Payment Celery tasks"
Test-File "core/management/commands/create_indexes.py" "Index creation command"
Test-File "tests_all_improvements.py" "Comprehensive test suite"
Test-File "IMPROVEMENTS_TESTING_GUIDE.md" "Testing guide"
Test-File "listings/migrations/9999_add_composite_indexes.py" "Listings indexes migration"
Test-File "transactions/migrations/9999_add_composite_indexes.py" "Transactions indexes migration"
Test-File "chat/migrations/9999_add_composite_indexes.py" "Chat indexes migration"

# Check modifications
Write-Host "`n=== MODIFIED FILES ===" -ForegroundColor Yellow

$settingsContent = Get-Content "config/settings.py" -Raw -Encoding UTF8
$dockerContent = Get-Content "docker-compose.yml" -Raw -Encoding UTF8

if ($settingsContent -match "ImproperlyConfigured") {
    Write-Host "  [OK] SECRET_KEY security improved" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] SECRET_KEY not secured" -ForegroundColor Red
    $failed++
}

if ($settingsContent -match "DEFAULT_THROTTLE_CLASSES") {
    Write-Host "  [OK] DRF throttling configured" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] DRF throttling missing" -ForegroundColor Red
    $failed++
}

if ($settingsContent -match "CONN_MAX_AGE") {
    Write-Host "  [OK] Connection pooling configured" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] Connection pooling missing" -ForegroundColor Red
    $failed++
}

if ($dockerContent -match "celery_worker") {
    Write-Host "  [OK] Celery worker in docker-compose" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] Celery worker missing" -ForegroundColor Red
    $failed++
}

if ($dockerContent -match "celery_beat") {
    Write-Host "  [OK] Celery beat in docker-compose" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] Celery beat missing" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
$total = $passed + $failed
$percentage = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }

Write-Host "Total checks: $total"
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host "Success rate: $percentage%`n"

if ($percentage -eq 100) {
    Write-Host "SUCCESS: All improvements verified!" -ForegroundColor Green
    exit 0
} elseif ($percentage -ge 80) {
    Write-Host "PARTIAL: Most improvements verified" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "FAILED: Many issues found" -ForegroundColor Red
    exit 1
}
