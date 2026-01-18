#!/bin/bash
#
# Build wheel distribution for Viper Terminal
#
# Usage: ./scripts/build/build-wheel.sh
#
# Output: dist/viper_terminal-X.X.X-py3-none-any.whl
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Building Viper Terminal Wheel ==="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Check Python version is 3.10+
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "Error: Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi

# Install build dependencies
echo ""
echo "Installing build dependencies..."
python3 -m pip install --quiet --upgrade pip build

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Build the wheel
echo ""
echo "Building wheel..."
python3 -m build --wheel

# Show result
echo ""
echo "=== Build Complete ==="
echo ""
echo "Wheel created:"
ls -la dist/*.whl
echo ""
echo "To install:"
echo "  pip install dist/$(ls dist/*.whl | head -1 | xargs basename)"
echo ""
echo "To upload to PyPI (if you have credentials):"
echo "  python3 -m pip install twine"
echo "  python3 -m twine upload dist/*"
