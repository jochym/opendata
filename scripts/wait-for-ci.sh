#!/bin/bash
# Wait for GitHub Actions CI to complete
# Polls gh run list and shows progress

set -e

TIMEOUT=1200  # 20 minutes
INTERVAL=30   # Check every 30 seconds
BRANCH=""

echo "🔄 Waiting for CI to complete..."
echo "   Timeout: ${TIMEOUT}s, Interval: ${INTERVAL}s"
echo ""

START_TIME=$(date +%s)
END_TIME=$((START_TIME + TIMEOUT))
LAST_STATUS=""

while true; do
    CURRENT_TIME=$(date +%s)
    if [[ $CURRENT_TIME -ge $END_TIME ]]; then
        echo "❌ Timeout waiting for CI"
        exit 1
    fi
    
    # Get latest run
    RUN_INFO=$(gh run list --branch "$BRANCH" --limit 1 --json status,conclusion,displayTitle,databaseId 2>/dev/null || echo "[]")
    
    if [[ -z "$RUN_INFO" || "$RUN_INFO" == "[]" ]]; then
        echo "⏳ No CI runs found yet..."
        sleep $INTERVAL
        continue
    fi
    
    STATUS=$(echo "$RUN_INFO" | jq -r '.[0].status')
    CONCLUSION=$(echo "$RUN_INFO" | jq -r '.[0].conclusion // "pending"')
    TITLE=$(echo "$RUN_INFO" | jq -r '.[0].displayTitle')
    RUN_ID=$(echo "$RUN_INFO" | jq -r '.[0].databaseId')
    
    # Status indicator
    if [[ "$STATUS" == "in_progress" ]]; then
        INDICATOR="🔄"
    elif [[ "$STATUS" == "queued" ]]; then
        INDICATOR="⏳"
    elif [[ "$CONCLUSION" == "success" ]]; then
        INDICATOR="✅"
    elif [[ "$CONCLUSION" == "failure" ]]; then
        INDICATOR="❌"
    else
        INDICATOR="⚪"
    fi
    
    # Only print if status changed
    CURRENT_STATUS="$STATUS/$CONCLUSION"
    if [[ "$CURRENT_STATUS" != "$LAST_STATUS" ]]; then
        echo "$INDICATOR $TITLE (#$RUN_ID) - Status: $STATUS, Conclusion: $CONCLUSION"
        LAST_STATUS="$CURRENT_STATUS"
    fi
    
    # Check if complete
    if [[ "$STATUS" == "completed" ]]; then
        if [[ "$CONCLUSION" == "success" ]]; then
            echo ""
            echo "✅ CI completed successfully!"
            exit 0
        else
            echo ""
            echo "❌ CI failed with conclusion: $CONCLUSION"
            echo ""
            echo "Failed jobs:"
            gh run view "$RUN_ID" --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name'
            echo ""
            echo "View logs: gh run watch $RUN_ID"
            exit 1
        fi
    fi
    
    sleep $INTERVAL
done
