@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
BREAK ON

echo ========================================
echo Elevator Scheduling Algorithm Launcher (No GUI)
echo ========================================
echo.

REM Set default parameters
set SIMULATOR_URL=http://127.0.0.1:8000
set CONTROLLER=look
set MAX_TICKS=2000
set DEBUG_MODE=--debug
set WAIT_VISUALIZATION=
set VISUALIZATION_WAIT_TIME=0
set TICK_DELAY=0

REM Parse command line arguments
:parse_args
if "%~1"=="" goto start_programs
if "%~1"=="--controller" (
    set CONTROLLER=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--max-ticks" (
    set MAX_TICKS=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--no-debug" (
    set DEBUG_MODE=
    shift
    goto parse_args
)
if "%~1"=="--help" (
    goto show_help
)
shift
goto parse_args

:show_help
echo Usage: start_no_gui.bat [options]
echo.
echo Options:
echo   --controller [algorithm]  Specify scheduling algorithm (default: bus)
echo   --max-ticks [number]       Specify maximum ticks (default: 2000)
echo   --no-debug                Disable debug mode
echo   --help                    Show this help message
echo.
echo Examples:
echo   start_no_gui.bat
echo   start_no_gui.bat --controller bus --max-ticks 1000
echo   start_no_gui.bat --no-debug
echo.
echo Note: This version runs without GUI and with no tick delays for maximum performance.
echo.
pause
exit /b 0

:start_programs
echo Configuration:
echo - Algorithm: %CONTROLLER%
echo - Max ticks: %MAX_TICKS%
echo - Debug mode: %DEBUG_MODE%
echo - Simulator URL: %SIMULATOR_URL%
echo - Mode: No GUI, No Tick Delay (Maximum Performance)
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found, please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

REM Check if poetry was installed
python -m poetry --version >nul 2>&1
if errorlevel 1 (
    echo Poetry not found. Installing Poetry for current user using pip...
    echo (This may take a minute)
    python -m pip install poetry
    if errorlevel 1 (
        echo ERROR: failed to install poetry via pip.
        echo You can also install Poetry manually: https://python-poetry.org/docs/#installation
        pause
        exit /b 1
    )
    echo Poetry installed (pip --user). Continuing...
) else (
    echo Poetry is already installed.
)

echo Installing project dependencies via Poetry...
python -m poetry install
if errorlevel 1 (
    echo ERROR: "poetry install" failed.
    echo Check pyproject.toml / poetry.lock and your network.
    pause
    exit /b 1
)

echo Activating venv
for /f "tokens=*" %%i in ('python -m poetry env activate') do set ACTIVATE_CMD=%%i
call %ACTIVATE_CMD%
if errorlevel 1 (
    echo WARNING: Failed to activate virtual environment. Continuing...
) else (
    echo Virtual environment activated successfully.
)

REM Check if elevator_saga module is available
python -c "import elevator_saga" >nul 2>&1
if errorlevel 1 (
    echo Error: elevator_saga module not found, please ensure it is properly installed
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo Error: main.py file not found
    pause
    exit /b 1
)

echo.
echo [1/2] Starting Elevator Saga Simulator...
echo Command: python -m elevator_saga.server.simulator
echo Simulator will run at %SIMULATOR_URL%
echo.

REM Start simulator in background
start /b python -m elevator_saga.server.simulator >nul 2>&1
echo Simulator started in background

echo Waiting for simulator to start...
timeout /t 2 /nobreak >nul

REM Check if simulator started successfully
echo Checking simulator status...
python -c "import requests; requests.get('%SIMULATOR_URL%/api/state', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo Warning: Simulator may not be fully started, but continuing...
) else (
    echo Simulator started successfully!
)

echo.
echo [2/2] Starting %CONTROLLER% scheduling algorithm...
set ALGORITHM_CMD=python main.py --controller %CONTROLLER% --max-ticks %MAX_TICKS% %DEBUG_MODE% --tick-delay %TICK_DELAY%
echo Command: %ALGORITHM_CMD%
echo.

REM Start algorithm in foreground (no background for better performance monitoring)
echo Starting algorithm in foreground for maximum performance...
echo Press Ctrl+C to stop the simulation.
echo.

REM Run algorithm in foreground
%ALGORITHM_CMD%

echo.
echo ========================================
echo Simulation completed!
echo ========================================
echo.
echo Press any key to exit...
pause
exit /b 0
