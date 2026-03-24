# LootLink Quick Cleanup (cross-platform PowerShell)

Write-Host "LootLink Quick Cleanup" -ForegroundColor Cyan
Write-Host "======================"

Write-Host "Cleaning Python cache..."
Get-ChildItem -Path . -Directory -Recurse -Filter "__pycache__" |
    Where-Object { $_.FullName -notmatch '\.venv|\.git' } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Get-ChildItem -Path . -Recurse -Include "*.pyc","*.pyo" |
    Where-Object { $_.FullName -notmatch '\.venv' } |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Cleaning backup files..."
Get-ChildItem -Path . -Recurse -Include "*.bak","*.tmp","*.old" |
    Where-Object { $_.FullName -notmatch '\.venv' } |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Cleaning test artifacts..."
Remove-Item -Path ".coverage" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "htmlcov" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path ".pytest_cache" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Cleanup complete!" -ForegroundColor Green
