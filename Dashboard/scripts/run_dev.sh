#!/bin/bash
# MonDashboard - Development Run Script (Linux/macOS)
# Starts Chrome with CDP and Flask app with unified logging

echo "=== MonDashboard Dev Mode ==="

# Set environment variables
export ENV="dev"
export CONSOLE_BRIDGE_MODE="cdp"  # cdp|inpage|off
export CDP_PORT="9222"
export LOG_LEVEL="INFO"

# Find Chrome executable
if command -v google-chrome &> /dev/null; then
    CHROME_EXE="google-chrome"
elif command -v chromium &> /dev/null; then
    CHROME_EXE="chromium"
elif command -v chromium-browser &> /dev/null; then
    CHROME_EXE="chromium-browser"
elif [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    CHROME_EXE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    CHROME_EXE=""
fi

if [ -n "$CHROME_EXE" ]; then
    echo "[CDP] Starting Chrome with remote debugging..."
    echo "      Executable: $CHROME_EXE"
    echo "      Port: $CDP_PORT"
    
    # Start Chrome in background
    "$CHROME_EXE" --remote-debugging-port=$CDP_PORT --user-data-dir=/tmp/chrome-dev-profile &
    CHROME_PID=$!
    
    echo "[CDP] Chrome started (PID: $CHROME_PID). Waiting 2 seconds..."
    sleep 2
else
    echo "[CDP] Chrome not found. CDP mode will not be available."
    echo "      Install Chrome or use CONSOLE_BRIDGE_MODE=inpage"
fi

# Start Flask app
echo "[Flask] Starting application..."
python run.pyw

echo "=== MonDashboard Stopped ==="

# Cleanup: Kill Chrome if it was started
if [ -n "$CHROME_PID" ]; then
    echo "[CDP] Stopping Chrome (PID: $CHROME_PID)..."
    kill $CHROME_PID 2>/dev/null
fi
