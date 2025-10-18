```bash
#!/bin/bash

# Enable error handling
set -e

echo "========================================"
echo "Elevator Scheduling Algorithm Launcher (No GUI)"
echo "========================================"
echo

# Set default parameters
SIMULATOR_URL="http://127.0.0.1:8000"
CONTROLLER="look"
MAX_TICKS=2000
DEBUG_MODE="--debug"
WAIT_VISUALIZATION=""
VISUALIZATION_WAIT_TIME=0
TICK_DELAY=0

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
        --help)
            echo "Usage: $0 [options]"
            echo
            echo "Options:"
            echo "  --controller [algorithm]  Specify scheduling algorithm (default: bus)"
            echo "  --max-ticks [number]      Specify maximum ticks (default: 2000)"
            echo "  --no-debug                Disable debug mode"
            echo "  --help                    Show this help message"
            echo
            echo "Examples:"
            echo "  $0"
            echo "  $0 --controller bus --max-ticks 1000"
            echo "  $0 --no-debug"
            echo
            echo "Note: This version runs without GUI and with no tick delays for maximum performance."
            echo
            read -p "Press Enter to exit..."
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
echo "- Simulator URL: $SIMULATOR_URL"
echo "- Mode: No GUI, No Tick Delay (Maximum Performance)"
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

echo
echo "[1/2] Starting Elevator Saga Simulator..."
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
echo "[2/2] Starting $CONTROLLER scheduling algorithm..."
ALGORITHM_CMD="python3 main.py --controller $CONTROLLER --max-ticks $MAX_TICKS $DEBUG_MODE --tick-delay $TICK_DELAY"
echo "Command: $ALGORITHM_CMD"
echo

echo "Starting algorithm in foreground for maximum performance..."
echo "Press Ctrl+C to stop the simulation."
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

    # Terminate simulator process
    echo "Terminating simulator process..."
    if ! pkill -f "python3.*elevator_saga.server.simulator" >/dev/null 2>&1; then
        echo "No simulator process found to terminate"
    else
        echo "Simulator process terminated"
    fi

    echo
    echo "Cleanup completed!"
    echo "All programs stopped."
    echo
    exit 0
}

# Run algorithm in foreground
$ALGORITHM_CMD

echo
echo "========================================"
echo "Simulation completed!"
echo "========================================"
echo
read -p "Press Enter to exit..."
exit 0
```