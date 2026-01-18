# Viper Terminal - Installation Guide

This guide provides detailed installation instructions for users of all technical levels.

## Table of Contents

- [Quick Install (Experienced Users)](#quick-install-experienced-users)
- [Detailed Installation](#detailed-installation)
  - [macOS](#macos)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
  - [Linux (Fedora/RHEL)](#linux-fedorarhel)
  - [Windows](#windows)
- [Installing from Wheel](#installing-from-wheel)
- [Installing from Source](#installing-from-source)
- [Standalone Binary](#standalone-binary)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## Quick Install (Experienced Users)

If you have Python 3.10+ and pip:

```bash
# Clone and install
git clone https://github.com/yourusername/viper.git
cd viper
pip install .

# Run
viper
```

Or install from a wheel:

```bash
pip install viper_terminal-0.3.1-py3-none-any.whl
viper
```

---

## Detailed Installation

### macOS

#### Step 1: Check if Python is installed

Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter).

```bash
python3 --version
```

If you see `Python 3.10` or higher, skip to Step 3. Otherwise, continue to Step 2.

#### Step 2: Install Python

**Option A: Using Homebrew (Recommended)**

If you don't have Homebrew, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python:
```bash
brew install python@3.11
```

**Option B: Download from python.org**

1. Go to https://www.python.org/downloads/
2. Download the latest Python 3.11 or 3.12 installer
3. Open the downloaded `.pkg` file
4. Follow the installation wizard
5. **Important:** When complete, open a NEW Terminal window

Verify installation:
```bash
python3 --version
```

#### Step 3: Download Viper

**Option A: Using git (if installed)**
```bash
cd ~
git clone https://github.com/yourusername/viper.git
cd viper
```

**Option B: Download ZIP**
1. Go to the Viper GitHub page
2. Click the green "Code" button
3. Click "Download ZIP"
4. Open Finder, go to Downloads
5. Double-click the ZIP to extract it
6. In Terminal:
```bash
cd ~/Downloads/viper-main
```

#### Step 4: Create a virtual environment (Recommended)

This keeps Viper's dependencies separate from your system Python:

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

#### Step 5: Install Viper

```bash
pip install .
```

Wait for the installation to complete. You may see some warnings - that's normal.

#### Step 6: Run Viper

```bash
viper
```

To run Viper in the future:
```bash
cd ~/viper  # or wherever you downloaded it
source venv/bin/activate
viper
```

---

### Linux (Ubuntu/Debian)

#### Step 1: Update system packages

```bash
sudo apt update
sudo apt upgrade -y
```

#### Step 2: Install Python and pip

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

Verify:
```bash
python3 --version  # Should be 3.10 or higher
```

If your version is below 3.10:
```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv
```

#### Step 3: Download Viper

```bash
cd ~
git clone https://github.com/yourusername/viper.git
cd viper
```

#### Step 4: Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 5: Install Viper

```bash
pip install .
```

#### Step 6: Run Viper

```bash
viper
```

---

### Linux (Fedora/RHEL)

#### Step 1: Install Python and dependencies

```bash
sudo dnf install -y python3 python3-pip git
```

#### Step 2: Download and install Viper

```bash
cd ~
git clone https://github.com/yourusername/viper.git
cd viper
python3 -m venv venv
source venv/bin/activate
pip install .
```

#### Step 3: Run Viper

```bash
viper
```

---

### Windows

#### Step 1: Install Python

1. Go to https://www.python.org/downloads/windows/
2. Download "Windows installer (64-bit)" for Python 3.11 or 3.12
3. Run the installer
4. **IMPORTANT:** Check the box "Add Python to PATH" at the bottom!
5. Click "Install Now"
6. When complete, click "Close"

Verify by opening **Command Prompt** (press `Win + R`, type `cmd`, press Enter):
```cmd
python --version
```

#### Step 2: Download Viper

**Option A: Using git**

If you have git installed:
```cmd
cd %USERPROFILE%
git clone https://github.com/yourusername/viper.git
cd viper
```

**Option B: Download ZIP**
1. Go to the Viper GitHub page
2. Click "Code" > "Download ZIP"
3. Extract to your Documents folder
4. In Command Prompt:
```cmd
cd %USERPROFILE%\Documents\viper-main
```

#### Step 3: Create virtual environment

```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of your prompt.

#### Step 4: Install Viper

```cmd
pip install .
```

#### Step 5: Run Viper

```cmd
viper
```

**Note:** Windows Terminal or the new Windows 11 terminal provides better display than the classic Command Prompt. You can install it from the Microsoft Store.

---

## Installing from Wheel

If you received a `.whl` file, this is the easiest installation method.

### What is a wheel?

A wheel is a pre-packaged Python application. You don't need to download source code or compile anything.

### Installation steps

1. Make sure Python 3.10+ is installed (see platform-specific instructions above)

2. Open Terminal (macOS/Linux) or Command Prompt (Windows)

3. Install the wheel:

**macOS/Linux:**
```bash
pip3 install /path/to/viper_terminal-0.3.1-py3-none-any.whl
```

**Windows:**
```cmd
pip install C:\path\to\viper_terminal-0.3.1-py3-none-any.whl
```

4. Run Viper:
```bash
viper
```

---

## Installing from Source

For developers or users who want the latest features.

### Prerequisites

- Python 3.10 or higher
- git
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/viper.git
cd viper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run
viper
```

### Running tests

```bash
pytest
```

### Type checking

```bash
mypy viper
```

---

## Standalone Binary

Standalone binaries are single-file executables that don't require Python to be installed.

### Downloading a binary

Check the [Releases](https://github.com/yourusername/viper/releases) page for pre-built binaries:

- `viper-macos` - macOS (Intel and Apple Silicon)
- `viper-linux` - Linux (x86_64)
- `viper-windows.exe` - Windows (64-bit)

### Running the binary

**macOS:**
```bash
chmod +x viper-macos
./viper-macos
```

**Linux:**
```bash
chmod +x viper-linux
./viper-linux
```

**Windows:**
Double-click `viper-windows.exe` or run from Command Prompt:
```cmd
viper-windows.exe
```

### Building your own binary

If binaries aren't available for your platform, you can build one:

```bash
# Install PyInstaller
pip install pyinstaller

# Build (from the viper directory)
./scripts/packaging/build-binary.sh  # macOS/Linux
# or
scripts\packaging\build-binary.bat   # Windows
```

The binary will be in the `dist/` folder.

---

## Troubleshooting

### "command not found: viper"

The `viper` command isn't in your PATH. Try:

```bash
python -m viper
```

Or make sure your virtual environment is activated:
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### "No module named 'viper'"

Viper isn't installed. Run:
```bash
pip install .
```

### "Python not found" or wrong version

Make sure Python 3.10+ is installed and in your PATH:
```bash
python3 --version
```

On Windows, try:
```cmd
py --version
```

### Display issues (garbled text, missing characters)

Viper uses Unicode characters for charts. Ensure your terminal:

1. Uses a font with good Unicode support (e.g., "Menlo", "Consolas", "DejaVu Sans Mono", "JetBrains Mono")
2. Has UTF-8 encoding enabled

**macOS Terminal:**
- Terminal > Preferences > Profiles > Text > Font

**Windows:**
- Use Windows Terminal (from Microsoft Store) instead of Command Prompt
- Or: Right-click title bar > Properties > Font > Select "Consolas"

**Linux:**
- Most modern terminals work out of the box
- If issues persist, try: `export LANG=en_US.UTF-8`

### "SSL: CERTIFICATE_VERIFY_FAILED"

On macOS, run the certificate installer:
```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Network/firewall issues

Viper needs internet access to fetch stock data. If you're behind a corporate firewall, you may need to configure proxy settings:

```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

---

## Uninstallation

### If installed with pip

```bash
pip uninstall viper-terminal
```

### If installed in a virtual environment

Simply delete the `viper` folder (which contains the `venv` folder).

### If using standalone binary

Delete the binary file.

---

## Getting Help

- **GitHub Issues:** https://github.com/yourusername/viper/issues
- **Press `?` in Viper** to see all keyboard shortcuts

---

## Version History

- **0.3.1** - Options chain support, enhanced indicators
- **0.2.0** - Technical indicators (SMA, EMA, RSI, MACD)
- **0.1.0** - Initial release with quotes, charts, and news
