@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 电梯调度算法启动脚本
echo ========================================
echo.

REM 设置默认参数
set SIMULATOR_URL=http://127.0.0.1:8000
set CONTROLLER=bus
set MAX_TICKS=2000
set DEBUG_MODE=--debug
set WAIT_VISUALIZATION=--wait-visualization
set VISUALIZATION_WAIT_TIME=5
set TICK_DELAY=0.5

REM 解析命令行参数
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
echo 使用方法: start.bat [选项]
echo.
echo 选项:
echo   --controller [算法]    指定调度算法 (默认: bus)
echo   --max-ticks [数量]     指定最大tick数 (默认: 2000)
echo   --no-debug            禁用调试模式
echo   --no-wait             不等待可视化程序
echo   --wait-time [秒数]    指定等待可视化程序的时间 (默认: 5)
echo   --tick-delay [秒数]   指定每个tick之间的延迟时间 (默认: 0.5)
echo   --help                显示此帮助信息
echo.
echo 示例:
echo   start.bat
echo   start.bat --controller bus --max-ticks 1000
echo   start.bat --no-debug --no-wait
echo   start.bat --wait-time 10
echo   start.bat --tick-delay 1.0
echo.
pause
exit /b 0

:start_programs
echo 配置信息:
echo - 调度算法: %CONTROLLER%
echo - 最大tick数: %MAX_TICKS%
echo - 调试模式: %DEBUG_MODE%
echo - 等待可视化: %WAIT_VISUALIZATION%
echo - 等待时间: %VISUALIZATION_WAIT_TIME%秒
echo - Tick延迟: %TICK_DELAY%秒
echo - 模拟器URL: %SIMULATOR_URL%
echo.

echo [1/3] 启动Elevator Saga模拟器...
echo 启动命令: python -m elevator_saga.server.simulator
echo 模拟器将在 %SIMULATOR_URL% 运行
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

REM 检查elevator_saga模块是否可用
python -c "import elevator_saga" >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到elevator_saga模块，请确保已正确安装
    pause
    exit /b 1
)

start "Elevator Saga Simulator" cmd /k "python -m elevator_saga.server.simulator"

echo 等待模拟器启动...
timeout /t 5 /nobreak >nul

REM 检查模拟器是否启动成功
echo 检查模拟器状态...
python -c "import requests; requests.get('%SIMULATOR_URL%/api/state', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo 警告: 模拟器可能未完全启动，但继续执行...
) else (
    echo 模拟器启动成功！
)

echo.
echo [2/3] 启动%CONTROLLER%调度算法...
set ALGORITHM_CMD=python main.py --controller %CONTROLLER% --max-ticks %MAX_TICKS% %DEBUG_MODE% %WAIT_VISUALIZATION% --visualization-wait-time %VISUALIZATION_WAIT_TIME% --tick-delay %TICK_DELAY%
echo 启动命令: %ALGORITHM_CMD%
echo.

REM 检查main.py是否存在
if not exist "main.py" (
    echo 错误: 未找到main.py文件
    pause
    exit /b 1
)

start "%CONTROLLER%调度算法" cmd /k "%ALGORITHM_CMD%"

echo 等待调度算法启动...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] 启动可视化程序...
echo 启动命令: python run_visualization.py
echo.

REM 检查run_visualization.py是否存在
if not exist "run_visualization.py" (
    echo 错误: 未找到run_visualization.py文件
    pause
    exit /b 1
)

REM 检查PyQt6是否可用
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo 警告: 未找到PyQt6，可视化程序可能无法启动
    echo 请运行: pip install PyQt6
)

start "电梯可视化" cmd /k "python run_visualization.py"

echo.
echo ========================================
echo 所有程序已启动完成！
echo ========================================
echo.
echo 已启动的程序：
echo - Elevator Saga 模拟器 (%SIMULATOR_URL%)
echo - %CONTROLLER%调度算法 (最大%MAX_TICKS%tick)
echo - 可视化程序 (PyQt6界面)
echo - 等待可视化: %WAIT_VISUALIZATION%
echo.
echo 注意事项：
echo 1. 请保持所有窗口打开，关闭任一窗口可能导致程序异常
echo 2. 模拟器需要先启动，调度算法和可视化程序依赖模拟器
echo 3. 如需停止程序，请依次关闭各个窗口
echo 4. 可视化程序需要PyQt6支持
echo.
echo 按任意键退出此脚本...
pause >nul