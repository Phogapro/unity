@echo off

title Cloud Phone Config Manager

echo =========================
echo UPDATE START
echo =========================

echo.
echo [1/5] Checkout main...
git checkout main

IF %ERRORLEVEL% NEQ 0 (
    echo CHECKOUT FAILED
    pause
    exit /b
)

echo.
echo [2/5] Pull latest...
git pull origin main

IF %ERRORLEVEL% NEQ 0 (
    echo PULL FAILED
    pause
    exit /b
)

echo.
echo [3/5] Generate YAML...
python generate.py

IF %ERRORLEVEL% NEQ 0 (
    echo GENERATE FAILED
    pause
    exit /b
)

echo.
echo [4/5] Git commit...
git add .

git commit -m "update 030826"

echo.
echo [5/5] Push GitHub...
git push origin main

IF %ERRORLEVEL% NEQ 0 (
    echo PUSH FAILED
    pause
    exit /b
)

echo.
echo =========================
echo UPDATE SUCCESS
echo =========================

pause