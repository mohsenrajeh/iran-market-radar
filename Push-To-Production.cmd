@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0.deployment\Invoke-ProductionPush.ps1" -RepoRoot "%~dp0"
set "exit_code=%errorlevel%"
echo.
if not "%exit_code%"=="0" echo Push to production was stopped. Review the error above.
if "%exit_code%"=="0" echo Push completed. GitHub checks and Coolify will continue automatically.
pause
exit /b %exit_code%
