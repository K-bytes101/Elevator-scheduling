```bash
#!/bin/bash

# Enable error handling
set -e

echo "========================================"
echo "Elevator Scheduling Algorithm Launcher"
echo "========================================"
echo

# Set default parameters
SIMULATOR_URL="http://127.0.0.1:8000"
CONTROLLER="look"
MAX_TICKS=2000
DEBUG_MODE="--debug"
WAIT_VISUALIZATION="--wait-visualization"
VISUALIZATION_WAIT_TIME=2.5
TICK_DELAY=0.3

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --controller)
            CONTROLLER="$2"
            shift 2
            ;;
        --max-ticks)
            MAX_TICKS="$2"
            shift 2
            ;;
        --no-debug)
            DEBUG_MODE=""
            shift
            ;;
        --no-wait)
            WAIT_VISUALIZATION=""
            shift
            ;;
        --wait-time)
            VISUALIZATION_WAIT_TIME="$2"
            shift 2
            ;;
        --tick-delay)
            TICK_DELAY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --controller [algorithm]  Specify scheduling algorithm (default: bus)"
            echo "  --max-ticks [number]      Specify maximum ticks (default: 10000)"
            echo "  --no-debug                Disable debug mode"
            echo "  --no-wait                 Don't wait for visualization"
            echo "  --wait-time [seconds]     Specify wait time for visualization (default: 2.5)"
            echo "  --tick-delay [seconds]    Specify delay between ticks (default: 0.3)"
            echo "  --help                    Show this help message"
            echo
            echo "Examples:"
            echo "  $0"
            echo "  $0 --controller bus --max-ticks 1000"
            echo "  $0 --no-debug --no-wait"
            echo "  $0 --wait-time 10"
            echo "  $0 --tick-delay 1.0"
            echo
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo "Configuration:"
echo "- Algorithm: $CONTROLLER"
echo "- Max ticks: $MAX_TICKS"
echo "- Debug mode: $DEBUG_MODE"
echo "- Wait visualization: $WAIT_VISUALIZATION"
echo "- Wait time: $VISUALIZATION_WAIT_TIME seconds"
echo "- Tick delay: $TICK_DELAY seconds"
echo "- Simulator URL: $SIMULATOR_URL"
echo

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python3 not found, please ensure Python3 is installed"
    echo "Install it with: sudo apt update && sudo apt install python3"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if Poetry is installed
if ! python3 -m poetry --version >/dev/null 2>&1; then
    echo "Poetry not found. Installing Poetry for current user using pip..."
    echo "(This may take a minute)"
    python3 -m pip install --user poetry
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install Poetry via pip."
        echo "You can also install Poetry manually: https://python-poetry.org/docs/#installation"
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "Poetry installed (pip --user). Continuing..."
else
    echo "Poetry is already installed."
fi

echo "Installing project dependencies via Poetry..."
python3 -m poetry install
if [ $? -ne 0 ]; then
    echo "ERROR: 'poetry install' failed."
    echo "Check pyproject.toml / poetry.lock and your network."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Activating venv"
VENV_PATH=$(python3 -m poetry env info -p)
if [ -z "$VENV_PATH" ]; then
    echo "ERROR: No virtual environment found. Run 'poetry install' to create one."
    read -p "Press Enter to exit..."
    exit 1
fi
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to activate virtual environment. Continuing..."
else
    echo "Virtual environment activated successfully."
fi

# Check if elevator_saga module is available
if ! python3 -c "import elevator_saga" >/dev/null 2>&1; then
    echo "Error: elevator_saga module not found, please ensure it is properly installed"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "Error: main.py file not found"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if run_visualization.py exists
if [ ! -f "run_visualization.py" ]; then
    echo "Error: run_visualization.py file not found"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if PyQt6 is available
if ! python3 -c "import PyQt6" >/dev/null 2>&1; then
    echo "Warning: PyQt6 not found, visualization may not start"
    echo "Please run: pip install PyQt6"
fi

echo
echo "[1/3] Starting Elevator Saga Simulator..."
echo "Command: python3 -m elevator_saga.server.simulator"
echo "Simulator will run at $SIMULATOR_URL"
echo

# Start simulator in background
python3 -m elevator_saga.server.simulator >/dev/null 2>&1 &
SIMULATOR_PID=$!
echo "Simulator started in background (PID: $SIMULATOR_PID)"

echo "Waiting for simulator to start..."
sleep 2

# Check if simulator started successfully
echo "Checking simulator status..."
if ! python3 -c "import requests; requests.get('$SIMULATOR_URL/api/state', timeout=2)" >/dev/null 2>&1; then
    echo "Warning: Simulator may not be fully started, but continuing..."
else
    echo "Simulator started successfully!"
fi

echo
echo "[2/3] Starting visualization program..."
echo "Command: python3 run_visualization.py"
echo

# Start visualization program in background
python3 run_visualization.py &
VISUALIZATION_PID=$!
echo "Visualization started in background (PID: $VISUALIZATION_PID)"

echo "Waiting for algorithm to start..."
sleep 2

echo
echo "[3/3] Starting $CONTROLLER scheduling algorithm..."
ALGORITHM_CMD="python3 main.py --controller $CONTROLLER --max-ticks $MAX_TICKS $DEBUG_MODE $WAIT_VISUALIZATION --visualization-wait-time $VISUALIZATION_WAIT_TIME --tick-delay $TICK_DELAY"
echo "Command: $ALGORITHM_CMD"
echo

# Start algorithm in background
$ALGORITHM_CMD >/dev/null 2>&1 &
ALGORITHM_PID=$!
echo "Algorithm started in background (PID: $ALGORITHM_PID)"

echo
echo "========================================"
echo "All programs started successfully!"
echo "========================================"
echo
echo "Started programs:"
echo "- Elevator Saga Simulator ($SIMULATOR_URL) [background]"
echo "- $CONTROLLER Algorithm (max $MAX_TICKS ticks) [background]"
echo "- Visualization Program (PyQt6 interface) [background]"
echo
echo "Elegant mode features:"
echo "1. Simulator and algorithm run in background, no extra windows"
echo "2. Visualization program runs in a separate process"
echo "3. Press Ctrl+C to stop all programs"
echo "4. More elegant program execution with cleaner interface"
echo
echo "Press Ctrl+C to stop all programs..."
echo

# Trap Ctrl+C for cleanup
trap cleanup INT

# Cleanup function
cleanup() {
    echo
    echo "========================================"
    echo "Cleaning up background processes..."
    echo "========================================"
    echo

    # Terminate background processes
    echo "Terminating Python processes..."
    if ! pkill -f "python3.*elevator_saga.server.simulator" >/dev/null 2>&1; then
        echo "No simulator process found to terminate"
    else
        echo "Simulator process terminated"
    fi
    if ! pkill -f "python3 run_visualization.py" >/dev/null 2>&1; then
        echo "No visualization process found to terminate"
    else
        echo "Visualization process terminated"
    fi
    if ! pkill -f "python3 main.py" >/dev/null 2>&1; then
        echo "No algorithm process found to terminate"
    else
        echo "Algorithm process terminated"
    fi

    echo
    echo "Cleanup completed!"
    echo "All programs stopped."
    echo
    exit 0
}

# Wait for user interrupt
while true; do
    sleep 1
done
```