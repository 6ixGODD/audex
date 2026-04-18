# Development Guide

This guide covers development setup and workflows for all platforms (Linux, macOS, and Windows).

## Package Management

Audex uses **uv** as the package manager and **setuptools** as the build backend.

### Installing uv

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**With pip (all platforms):**
```bash
pip install uv
```

### System Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-pyqt6 python3-pyqt6.qtwebengine \
    portaudio19-dev ffmpeg sqlite3 network-manager \
    libfcitx5-qt6-1 alsa-utils gcc build-essential
```

#### macOS
```bash
brew install portaudio ffmpeg sqlite3
pip install PyQt6 PyQt6-WebEngine
```

#### Windows
- **Python 3.10-3.13**: Download from [python.org](https://www.python.org/downloads/)
- **PortAudio**: Bundled with PyAudio wheel
- **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **SQLite3**: Included with Python
- **Git**: Download from [git-scm.com](https://git-scm.com/download/win)

---

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/6ixGODD/audex.git
cd audex
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv sync --all-extras

# Or install specific groups
uv sync --extra dev      # Development tools
uv sync --extra test     # Testing tools
uv sync --extra docs     # Documentation tools
```

### 3. Verify Installation

```bash
uv run python -m audex --version
```

---

## Running Commands

Execute commands in the virtual environment using `uv run`:

```bash
# Run the application
uv run python -m audex -c config.yaml

# Run tests
uv run pytest

# Run linters
uv run ruff check audex/
uv run mypy audex/

# Build documentation
uv run mkdocs serve
```

---

## Building the Package

Build wheel and source distribution:

```bash
uv build
```

Output files in `dist/`:
- `audex-{version}-py3-none-any.whl`
- `audex-{version}.tar.gz`

---

## Makefile Commands

The project includes a Makefile for common tasks:

```bash
# Install dependencies
make install

# Run tests
make test

# Run linters
make lint

# Build package
make build

# View all available commands
make help
```

---

## Version Management

### Using bump Script

**Linux/macOS:**
```bash
# Show help
./scripts/bump.sh --help

# Bump version (dry run)
./scripts/bump.sh 1.2.3 --dry-run

# Bump version (actual)
./scripts/bump.sh 1.2.3

# Bump without git operations
./scripts/bump.sh 1.2.3 --no-git
```

**Windows (PowerShell):**
```powershell
# Show help
.\scripts\bump.ps1 -Help

# Bump version (dry run)
.\scripts\bump.ps1 1.2.3 -DryRun

# Bump version (actual)
.\scripts\bump.ps1 1.2.3

# Bump without git operations
.\scripts\bump.ps1 1.2.3 -NoGit

# Bump without pushing to remote
.\scripts\bump.ps1 1.2.3 -NoPush
```

The bump script automatically:
- Updates `VERSION` file
- Updates `pyproject.toml`
- Updates `audex/__init__.py`
- Regenerates configuration files
- Creates git commit and tag (optional)
- Pushes to remote (optional)

---

## Dependency Management

### Add a Dependency

```bash
uv add <package-name>
```

### Add a Development Dependency

```bash
uv add --dev <package-name>
```

### Remove a Dependency

```bash
uv remove <package-name>
```

### Update Dependencies

```bash
uv sync --upgrade
```

### Lock Dependencies

```bash
uv lock
```

---

## Testing

### Run All Tests

```bash
uv run pytest
```

### Run with Coverage

```bash
uv run pytest --cov=audex --cov-report=html --cov-report=term
```

### Run Specific Tests

```bash
uv run pytest tests/test_something.py
```

### Using Makefile

```bash
make test           # Run all tests
make test-cov       # Run with coverage
```

---

## Code Quality

### Linting

```bash
# Ruff
uv run ruff check audex/

# MyPy
uv run mypy audex/
```

### Formatting

```bash
uv run ruff format audex/
```

### Using Makefile

```bash
make lint           # Run linters
make format         # Format code
make check          # Format + lint
```

---

## Documentation

### Serve Locally

```bash
uv run mkdocs serve
# Visit http://127.0.0.1:8000
```

### Build Static Site

```bash
uv run mkdocs build
# Output in site/
```

### Deploy to GitHub Pages

```bash
uv run mkdocs gh-deploy
```

### Using Makefile

```bash
make docs-serve     # Serve locally
make docs-build     # Build static site
make docs-deploy    # Deploy to GitHub Pages
```

---

## Platform-Specific Notes

### Windows

#### PowerShell Execution Policy

If you encounter execution policy errors:

```powershell
# Check current policy
Get-ExecutionPolicy

# Allow local scripts (run as Administrator)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Virtual Environment Activation

uv manages the virtual environment automatically. To activate manually:

```powershell
# Activate
.\.venv\Scripts\Activate.ps1

# Deactivate
deactivate
```

#### Long Paths

Enable long paths in Windows (run as Administrator):

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

Configure Git to use long paths:

```powershell
git config --global core.longpaths true
```

#### Audio Devices

List available audio devices:

```powershell
uv run python -c "import pyaudio; pa = pyaudio.PyAudio(); [print(f'{i}: {pa.get_device_info_by_index(i)[\"name\"]}') for i in range(pa.get_device_count())]"
```

### Linux

#### PyQt6 Installation

Install PyQt6 from system packages:

```bash
sudo apt-get install python3-pyqt6 python3-pyqt6.qtwebengine
```

#### Audio Configuration

Make sure your user is in the `audio` group:

```bash
sudo usermod -a -G audio $USER
```

---

## IDE Setup

### Visual Studio Code

**Recommended Extensions:**
- Python
- Pylance
- Ruff
- PowerShell (Windows)

**Workspace Settings (`.vscode/settings.json`):**

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

### PyCharm

1. Set Python interpreter to `.venv/bin/python` (Linux/macOS) or `.venv\Scripts\python.exe` (Windows)
2. Mark `audex` directory as Sources Root
3. Enable external tools for ruff and mypy

---

## Common Workflows

### Starting Development

```bash
git clone https://github.com/6ixGODD/audex.git
cd audex
uv sync --all-extras
make dev-gen  # Generate code if needed
```

### Making Changes

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Make your changes

# Run tests
make test

# Check code quality
make check

# Commit
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

### Preparing a Release

```bash
# Update version (Linux/macOS)
./scripts/bump.sh 1.2.3

# Update version (Windows)
.\scripts\bump.ps1 1.2.3

# This will:
# - Update VERSION, pyproject.toml, __init__.py
# - Regenerate config files
# - Create git commit and tag
# - Push to remote (with confirmation)
```

---

## Troubleshooting

### uv command not found

```bash
# Install uv
pip install uv

# Verify installation
uv --version
```

### Dependencies out of sync

```bash
# Re-sync dependencies
uv sync --reinstall
```

### Build errors

```bash
# Clean and rebuild
make clean
uv build
```

### Lock file conflicts

```bash
# Regenerate lock file
uv lock --upgrade
```

---

## Getting Help

- **Documentation**: https://6ixgodd.github.io/audex/
- **Issues**: https://github.com/6ixGODD/audex/issues
- **Discussions**: https://github.com/6ixGODD/audex/discussions
