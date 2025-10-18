@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
BREAK ON

echo ========================================
echo Elevator Scheduling Algorithm Launcher
echo ========================================
echo.

REM Set default parameters
set SIMULATOR_URL=http://127.0.0.1:8000
set CONTROLLER=look
set MAX_TICKS=2000
set DEBUG_MODE=--debug
set WAIT_VISUALIZATION=--wait-visualization
set VISUALIZATION_WAIT_TIME=2.5
set TICK_DELAY=0.3

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
if "%~1"=="--no-wait" (
    set WAIT_VISUALIZATION=
    shift
    goto parse_args
)
if "%~1"=="--wait-time" (
    set VISUALIZATION_WAIT_TIME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--tick-delay" (
    set TICK_DELAY=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" (
    goto show_help
)
shift
goto parse_args

:show_help
echo Usage: start.bat [options]
echo.
echo Options:
echo   --controller [algorithm]  Specify scheduling algorithm (default: bus)
echo   --max-ticks [number]       Specify maximum ticks (default: 10000)
echo   --no-debug                Disable debug mode
echo   --no-wait                 Don't wait for visualization
echo   --wait-time [seconds]     Specify wait time for visualization (default: 2.5)
echo   --tick-delay [seconds]    Specify delay between ticks (default: 0.3)
echo   --help                    Show this help message
echo.
echo Examples:
echo   start.bat
echo   start.bat --controller bus --max-ticks 1000
echo   start.bat --no-debug --no-wait
echo   start.bat --wait-time 10
echo   start.bat --tick-delay 1.0
echo.
pause
exit /b 0

:start_programs
echo Configuration:
echo - Algorithm: %CONTROLLER%
echo - Max ticks: %MAX_TICKS%
echo - Debug mode: %DEBUG_MODE%
echo - Wait visualization: %WAIT_VISUALIZATION%
echo - Wait time: %VISUALIZATION_WAIT_TIME% seconds
echo - Tick delay: %TICK_DELAY% seconds
echo - Simulator URL: %SIMULATOR_URL%
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

REM Check if run_visualization.py exists
if not exist "run_visualization.py" (
    echo Error: run_visualization.py file not found
    pause
    exit /b 1
)

REM Check if PyQt6 is available
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Warning: PyQt6 not found, visualization may not start
    echo Please run: pip install PyQt6
)

echo.
echo [1/3] Starting Elevator Saga Simulator...
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
echo [2/3] Starting visualization program...
echo Command: python run_visualization.py
echo.

REM Start visualization program first for better display (keep window)
start "Elevator Visualization" python run_visualization.py

echo Waiting for algorithm to start...
timeout /t 2 /nobreak >nul

echo.
echo [3/3] Starting %CONTROLLER% scheduling algorithm...
set ALGORITHM_CMD=python main.py --controller %CONTROLLER% --max-ticks %MAX_TICKS% %DEBUG_MODE% %WAIT_VISUALIZATION% --visualization-wait-time %VISUALIZATION_WAIT_TIME% --tick-delay %TICK_DELAY%
echo Command: %ALGORITHM_CMD%
echo.

REM Start algorithm in background
start /b %ALGORITHM_CMD% >nul 2>&1
echo Algorithm started in background

echo.
echo ========================================
echo All programs started successfully!
echo ========================================
echo.
echo Started programs:
echo - Elevator Saga Simulator (%SIMULATOR_URL%) [background]
echo - %CONTROLLER% Algorithm (max %MAX_TICKS% ticks) [background]
echo - Visualization Program (PyQt6 interface) [separate window]
echo.
echo Elegant mode features:
echo 1. Simulator and algorithm run in background, no extra windows
echo 2. Only visualization program creates separate window
echo 3. Closing this command window will terminate all background processes
echo 4. More elegant program execution with cleaner interface
echo.
echo Press Ctrl+C or close this window to stop all programs...
echo.

REM Set up interrupt handling
echo Monitoring program status...
echo.

REM Wait for user interrupt
:wait_loop
timeout /t 1 /nobreak >nul
if errorlevel 1 goto cleanup
goto wait_loop

:cleanup
echo.
echo ========================================
echo Cleaning up background processes...
echo ========================================
echo.

REM Terminate Python processes
echo Terminating Python processes...
taskkill /F /IM python.exe >nul 2>&1
if errorlevel 1 (
    echo No Python processes found to terminate
) else (
    echo Python processes terminated
)

echo.
echo Cleanup completed!
echo All programs stopped.
echo.
pause
exit /b 0