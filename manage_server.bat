@echo off
title IRAN MARKET RADAR - SERVER MANAGER
chcp 65001 > nul

cd /d "%~dp0"

:MENU
cls
echo ======================================================================
echo   IRAN MARKET RADAR - SERVER MANAGER & DOCKER CONTROLLER
echo ======================================================================
echo  1. RUN LOCAL ENVIRONMENT (FastAPI: 8000 + Next.js: 3000)
echo  2. RUN LOCAL DOCKER STACK (Web: 3742 ^| API: 8742 ^| DB: 5742)
echo  3. STOP LOCAL DOCKER STACK
echo  4. DEPLOY COMPLETE SYSTEM TO REMOTE SERVER (193.242.125.76)
echo  5. CHECK REMOTE SERVER DOCKER STATUS
echo  6. RUN AUTOMATED TEST SUITE (pytest 46/46)
echo  7. RUN IMMEDIATE TRADING RADAR SCAN CYCLE
echo  8. EXIT
echo ======================================================================
echo.

set choice=
set /p choice="Select an option (1-8): "

if "%choice%"=="1" goto RUN_LOCAL
if "%choice%"=="2" goto RUN_DOCKER
if "%choice%"=="3" goto STOP_DOCKER
if "%choice%"=="4" goto DEPLOY_SERVER
if "%choice%"=="5" goto SERVER_STATUS
if "%choice%"=="6" goto RUN_TESTS
if "%choice%"=="7" goto RUN_CYCLE
if "%choice%"=="8" goto EXIT
goto MENU

:RUN_LOCAL
cls
echo ======================================================================
echo  STARTING LOCAL DEVELOPMENT ENVIRONMENT...
echo ======================================================================
echo  Backend API:  http://localhost:8742/docs
echo  Frontend UI:  http://localhost:3742
echo  Credentials:  admin / radar2026
echo ======================================================================
start "Iran Market Radar - API" cmd /k "python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8742 --reload"
timeout /t 2 > nul
start "Iran Market Radar - Web" cmd /k "cd apps\web && npm run dev"
goto MENU

:RUN_DOCKER
cls
echo ======================================================================
echo  STARTING LOCAL DOCKER CONTAINERS...
echo ======================================================================
echo  Web UI:      http://localhost:3742
echo  Backend API: http://localhost:8742/docs
echo  Postgres:    localhost:5742
echo  Redis:       localhost:6742
echo ======================================================================
docker compose up -d --build
echo.
docker compose ps
echo.
pause
goto MENU

:STOP_DOCKER
cls
echo ======================================================================
echo  STOPPING LOCAL DOCKER CONTAINERS...
echo ======================================================================
docker compose down
echo.
echo Docker containers stopped.
pause
goto MENU

:DEPLOY_SERVER
cls
echo ======================================================================
echo  DEPLOYING TO PRODUCTION SERVER (193.242.125.76)...
echo ======================================================================
echo  This will bundle the codebase, upload it to the remote server,
echo  and rebuild the Docker stack on dedicated production ports:
echo    - Frontend UI:  http://193.242.125.76:3742
echo    - Backend API:  http://193.242.125.76:8742
echo    - Capital:      10 Billion Tomans (Paper Portfolio)
echo    - Auth:         admin / radar2026 (Persistent 30-Day Session)
echo ======================================================================
set confirm=n
set /p confirm="Are you ready to deploy? (y/N): "
if /i "%confirm%" neq "y" goto MENU

python tools\deploy_to_server.py
echo.
pause
goto MENU

:SERVER_STATUS
cls
echo ======================================================================
echo  CHECKING REMOTE DOCKER CONTAINER STATUS...
echo ======================================================================
python tools\check_server_status.py
echo.
pause
goto MENU

:RUN_TESTS
cls
echo ======================================================================
echo  RUNNING FULL PYTEST TEST SUITE...
echo ======================================================================
python -m pytest tests/ -v
echo.
pause
goto MENU

:RUN_CYCLE
cls
echo ======================================================================
echo  EXECUTING ONE RADAR & AUTO-TRADING CYCLE...
echo ======================================================================
python tools\run_single_cycle.py
echo.
echo Cycle completed.
pause
goto MENU

:EXIT
exit /b 0
