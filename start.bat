@echo off
echo Starting Elevator Simulation...
:: (创建虚拟环境)

:: 安装依赖
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies. Please check requirements.txt and try again.
    pause
    exit /b %ERRORLEVEL%
)

:: 启动模拟器（在后台运行）
echo Starting elevator simulator...
start /B python -m elevator_saga.server.simulator
if %ERRORLEVEL% neq 0 (
    echo Failed to start simulator. Please ensure elevator_saga is installed correctly.
    pause
    exit /b %ERRORLEVEL%
)

:: 等待几秒确保模拟器启动
timeout /t 2 /nobreak >nul

:: 启动主程序
echo Starting main application...
python main.py
if %ERRORLEVEL% neq 0 (
    echo Failed to start main application. Please check main.py and try again.
    pause
    exit /b %ERRORLEVEL%
)

pause