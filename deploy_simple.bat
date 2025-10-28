@echo off
chcp 65001 >nul
echo ================================================
echo   DEPLOY TO SERVER 91.218.245.178
echo ================================================
echo.
echo Connecting to server...
echo.

ssh root@91.218.245.178 "cd /opt/lootlink && git pull origin main && chmod +x FIX_SERVER_NOW.sh && ./FIX_SERVER_NOW.sh"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo   DEPLOY COMPLETED!
    echo ================================================
    echo.
    echo Open in browser: http://91.218.245.178
    echo.
) else (
    echo.
    echo ERROR: Could not connect to server
    echo.
    echo Try manually:
    echo ssh root@91.218.245.178
    echo cd /opt/lootlink
    echo git pull origin main
    echo chmod +x FIX_SERVER_NOW.sh
    echo ./FIX_SERVER_NOW.sh
    echo.
)

pause

