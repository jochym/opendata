#!/bin/bash
# Automated E2E test runner
# Starts app, runs tests, stops app - fully automated

set -e

echo "=========================================="
echo "OpenData Tool - E2E Test Runner"
echo "=========================================="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    pkill -9 -f "main.py" 2>/dev/null || true
    pkill -9 Xvfb 2>/dev/null || true
    echo "✅ Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Kill any existing instances
echo "🔍 Checking for existing instances..."
pkill -9 -f "main.py" 2>/dev/null || true
pkill -9 Xvfb 2>/dev/null || true
sleep 2

# Set display for GUI tests
export DISPLAY=:99
echo "🖥️  Starting Xvfb..."
Xvfb :99 -screen 0 1280x1024x24 -noreset &
XVFB_PID=$!
sleep 2

# Start app
cd "$(dirname "$0")/.."
echo "🚀 Starting OpenData app with API..."
python src/opendata/main.py --headless --api --port 8080 > /tmp/app_test.log 2>&1 &
APP_PID=$!

# Wait for app to be ready
echo "⏳ Waiting for app to be ready (max 45s)..."
for i in {1..45}; do
    if curl -s http://127.0.0.1:8080/api/projects > /dev/null 2>&1; then
        echo "✅ App and API are ready!"
        break
    fi
    if [ $i -eq 45 ]; then
        echo "❌ App failed to start within 45 seconds"
        echo "=== App Log ==="
        cat /tmp/app_test.log
        exit 1
    fi
    sleep 1
done

echo ""
echo "=========================================="
echo "Running E2E Tests"
echo "=========================================="
echo ""

# Run tests
pytest tests/e2e/ -v -m "local_only" --tb=short "$@"
TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
else
    echo "❌ TESTS FAILED (exit code: $TEST_EXIT_CODE)"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
