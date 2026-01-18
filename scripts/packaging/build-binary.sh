#!/bin/bash
#
# Build standalone binary for Viper Terminal using PyInstaller
#
# Usage: ./scripts/build/build-binary.sh
#
# Output: dist/viper (executable)
#
# Prerequisites:
#   - Python 3.10+
#   - pip install pyinstaller
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Building Viper Terminal Standalone Binary ==="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows";;
    *)          PLATFORM="unknown";;
esac
echo "Platform: $PLATFORM"

# Check for PyInstaller
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo ""
    echo "PyInstaller not found. Installing..."
    python3 -m pip install --quiet pyinstaller
fi

# Install viper dependencies first (PyInstaller needs them)
echo ""
echo "Installing dependencies..."
python3 -m pip install --quiet .

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build/ dist/

# Build the binary
echo ""
echo "Building binary (this may take a few minutes)..."
python3 -m PyInstaller scripts/build/viper.spec --noconfirm

# Check if build succeeded
if [ -f "dist/viper" ]; then
    # Rename with platform suffix
    BINARY_NAME="viper-$PLATFORM"
    if [ "$PLATFORM" = "macos" ]; then
        # Check architecture on macOS
        ARCH="$(uname -m)"
        if [ "$ARCH" = "arm64" ]; then
            BINARY_NAME="viper-macos-arm64"
        else
            BINARY_NAME="viper-macos-x64"
        fi
    fi

    mv "dist/viper" "dist/$BINARY_NAME"
    chmod +x "dist/$BINARY_NAME"

    echo ""
    echo "=== Build Complete ==="
    echo ""
    echo "Binary created:"
    ls -lh "dist/$BINARY_NAME"
    echo ""
    echo "To run:"
    echo "  ./dist/$BINARY_NAME"
    echo ""
    echo "To distribute, copy this single file to the target machine."
else
    echo ""
    echo "Error: Build failed. Check the output above for errors."
    exit 1
fi
