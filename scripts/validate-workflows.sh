#!/bin/bash
# Validate GitHub Actions workflows for common Python syntax errors

set -e

echo "🔍 Validating GitHub Actions workflows..."

for file in .github/workflows/*.yml; do
    echo "Checking $file..."
    
    # Validate YAML syntax
    python3 -c "import yaml; yaml.safe_load(open('$file'))" || {
        echo "❌ YAML syntax error in $file"
        exit 1
    }
    
    # Check for multi-line Python strings that might cause IndentationError
    if grep -q 'python3 -c "$' "$file"; then
        echo "⚠️  Warning: Multi-line Python string found in $file"
        echo "   This may cause IndentationError in containers."
        echo "   Consider using single-line python3 -c or a script file."
    fi
    
    # Check for 'source' command (not available in sh)
    if grep -q '^[[:space:]]*source ' "$file"; then
        echo "❌ Found 'source' command in $file"
        echo "   Use '. command' instead for POSIX shell compatibility"
        exit 1
    fi
done

echo "✅ All workflows validated successfully"
