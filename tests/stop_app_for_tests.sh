#!/bin/bash
# Helper script to stop app after E2E tests

echo "🛑 Stopping OpenData app..."
pkill -9 -f "main.py" 2>/dev/null
pkill -9 Xvfb 2>/dev/null
echo "✅ App stopped"
