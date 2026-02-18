#!/bin/bash
# Helper script to start app for E2E tests

echo "🚀 Starting OpenData app for E2E tests..."

# Kill any existing instances
pkill -9 -f "main.py" 2>/dev/null
pkill -9 Xvfb 2>/dev/null
sleep 2

# Set display for GUI tests
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -noreset &
XVFB_PID=$!
echo "✅ Xvfb started (PID: $XVFB_PID)"

# Start app
cd "$(dirname "$0")/.."
python src/opendata/main.py --headless --api --port 8080 &
APP_PID=$!
echo "✅ App started (PID: $APP_PID)"

# Wait for app to be ready
echo "⏳ Waiting for app to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8080/api/projects > /dev/null 2>&1; then
        echo "✅ App and API are ready!"
        echo ""
        echo "📝 Run your tests now:"
        echo "   pytest tests/e2e/ -v -m 'local_only'"
        echo ""
        echo "🛑 To stop the app:"
        echo "   kill $APP_PID $XVFB_PID"
        echo "   or run: tests/stop_app_for_tests.sh"
        exit 0
    fi
    sleep 1
done

echo "❌ App failed to start within 30 seconds"
kill $APP_PID $XVFB_PID 2>/dev/null
exit 1
