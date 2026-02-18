#!/bin/bash
# Complete test runner - runs all tests with proper setup

set -e

echo "=========================================="
echo "OpenData Tool - Complete Test Suite"
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

trap cleanup EXIT

# Kill existing
pkill -9 -f "main.py" 2>/dev/null || true
pkill -9 Xvfb 2>/dev/null || true
sleep 2

# Set display
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 -noreset &
sleep 2

# Start app
cd "$(dirname "$0")/.."
python src/opendata/main.py --headless --api --port 8080 &
sleep 15

echo ""
echo "=========================================="
echo "1. Running CI/CD Safe Tests"
echo "=========================================="
pytest tests/unit/ tests/integration/ -v -m "not ai_interaction and not local_only" --tb=short

echo ""
echo "=========================================="
echo "2. Running AI Tests (with app running)"
echo "=========================================="
pytest tests/unit/ai/ tests/end_to_end/ -v -m "ai_interaction" --tb=short

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "✅ All tests completed!"
