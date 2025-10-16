@echo off
echo Testing start.bat components...

echo.
echo [1] Testing Python availability...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
) else (
    echo Python found
)

echo.
echo [2] Testing elevator_saga module...
python -c "import elevator_saga"
if errorlevel 1 (
    echo ERROR: elevator_saga module not found
    pause
    exit /b 1
) else (
    echo elevator_saga module found
)

echo.
echo [3] Testing main.py existence...
if not exist "main.py" (
    echo ERROR: main.py not found
    pause
    exit /b 1
) else (
    echo main.py found
)

echo.
echo [4] Testing run_visualization.py existence...
if not exist "run_visualization.py" (
    echo ERROR: run_visualization.py not found
    pause
    exit /b 1
) else (
    echo run_visualization.py found
)

echo.
echo [5] Testing PyQt6 module...
python -c "import PyQt6"
if errorlevel 1 (
    echo WARNING: PyQt6 not found
) else (
    echo PyQt6 module found
)

echo.
echo All checks passed!
echo Starting simulator test...

echo.
echo [6] Starting simulator...
start /b python -m elevator_saga.server.simulator >nul 2>&1
echo Simulator started in background

echo Waiting for simulator...
timeout /t 3 /nobreak >nul

echo Testing simulator connection...
python -c "import requests; requests.get('http://127.0.0.1:8000/api/state', timeout=2)"
if errorlevel 1 (
    echo WARNING: Simulator connection failed
) else (
    echo Simulator connection successful!
)

echo.
echo [7] Starting algorithm...
set ALGORITHM_CMD=python main.py --controller bus --max-ticks 5 --debug --wait-visualization --visualization-wait-time 2.5 --tick-delay 0.5
echo Command: %ALGORITHM_CMD%
start /b %ALGORITHM_CMD% >nul 2>&1
echo Algorithm started in background

echo Waiting for algorithm...
timeout /t 3 /nobreak >nul

echo.
echo [8] Starting visualization...
start "Test Visualization" python run_visualization.py
echo Visualization started

echo.
echo Test completed!
echo Press any key to cleanup...
pause

echo Cleaning up...
taskkill /F /IM python.exe >nul 2>&1
echo Cleanup completed
