<div align="center">

![Audex Logo](docs/assets/logo.svg)

# Audex

[![PyPI version](https://badge.fury.io/py/audex.svg)](https://pypi.org/project/audex/)
[![Python](https://img.shields.io/pypi/pyversions/audex.svg)](https://pypi.org/project/audex/)
[![License](https://img.shields.io/github/license/6ixGODD/audex.svg)](https://github.com/6ixGODD/audex/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/6ixGODD/audex.svg)](https://github.com/6ixGODD/audex/stargazers)

Derived from "Audio Exchange", Smart Medical Recording & Transcription System with voice recognition and speaker identification.

[Documentation](https://6ixgodd.github.io/audex/) • [Installation Guide](https://6ixgodd.github.io/audex/installation/) • [API Reference](https://6ixgodd.github.io/audex/reference/)

English | [简体中文](README.zh-CN.md)

</div>

---

## System Requirements

- Python 3.10-3.13
- Poetry
- PortAudio
- FFmpeg
- SQLite3
- PyQt6 (Linux: install from system packages)
- NetworkManager (Linux: for WiFi connectivity)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-pyqt6 python3-pyqt6.qtwebengine \
    portaudio19-dev ffmpeg sqlite3 network-manager \
    libfcitx5-qt6-1 alsa-utils gcc build-essential
```

**macOS:**
```bash
brew install portaudio ffmpeg sqlite3
pip install PyQt6 PyQt6-WebEngine
```

**Windows:**
- PortAudio is bundled with PyAudio wheel
- FFmpeg: Download from https://ffmpeg.org/download.html and add to `PATH`
- SQLite3: Included with Python installation

---

## Installation

### From PyPI

```bash
pip install audex
```

### From Source

```bash
git clone https://github.com/6ixGODD/audex.git
cd audex
poetry install
```

### DEB Package (Debian/Ubuntu/Raspberry Pi)

Download the appropriate DEB package for your architecture from [Releases](https://github.com/6ixGODD/audex/releases).

For detailed installation instructions, see [Installation Guide](https://6ixgodd.github.io/audex/installation/).

**Quick Install:**

```bash
# Download and install
sudo dpkg -i audex_{version}_arm64.deb
sudo apt-get install -f

# Run configuration wizard
sudo audex-setup

# Start application
sudo audex
```

---

## Usage

### Run Application

```bash
# Start with config file
audex -c config.yaml

# Using installed package
python -m audex -c config.yaml
```

### Initialize Configuration

```bash
# Generate default configuration
audex init gencfg --format yaml --output config.yaml

# Generate system configuration (Linux)
audex init gencfg --format system --output /etc/audex/config.yml --platform linux
```

### Initialize VPR Group

```bash
# Initialize voice print recognition group
audex init vprgroup --config config.yaml
```

### File Export Server

```bash
# Start file export server
audex serve --config config.yaml
```

---

## Configuration

Configuration file structure:

```yaml
core:
  app:
    app_name: Audex
    native: true
  logging:
    targets:
      - logname: stdout
        loglevel: info
  audio:
    sample_rate: 16000

provider:
  transcription:
    provider: dashscope
    dashscope:
      credential:
        api_key: <YOUR_API_KEY>

  vpr:
    provider: xfyun
    xfyun:
      credential:
        app_id: <YOUR_APP_ID>
        api_key: <YOUR_API_KEY>
        api_secret: <YOUR_API_SECRET>

infrastructure:
  sqlite:
    uri: "sqlite+aiosqlite:///path/to/audex.db"
  store:
    type: localfile
    base_url: /path/to/store
```

See `config.example.yml` for complete configuration options.

---

## Development

### Install Development Dependencies

```bash
# Development environment
poetry install --extras dev

# Testing environment
poetry install --extras test

# Documentation environment
poetry install --extras docs
```

### Build Package

```bash
# Build wheel and sdist
poetry build

# Output: dist/audex-{version}-py3-none-any.whl
```

### Run Tests

```bash
poetry install --extras test
poetry run pytest
```

### Documentation

```bash
poetry install --extras docs
poetry run mkdocs serve

# Visit: http://127.0.0.1:8000
```

---

## DEB Package Development

### Build DEB Package

**Prerequisites:**
- Docker

**Build:**

```bash
cd packaging/linux

# Build for ARM64 (Raspberry Pi)
./build.sh

# Build for AMD64
./build.sh amd64
```

**Output:** `dist/audex_{version}_{arch}.deb`

### Test DEB Package

```bash
cd packaging/linux
./test.sh arm64
```

**Inside test container:**

```bash
# Install package
dpkg -i /tmp/audex.deb
apt-get install -f

# Verify installation
which audex
audex --version

# View configurations
cat /etc/audex/config.system.yml
cat /etc/audex/config.example.yml

# Run configuration wizard
audex-setup

# Exit container
exit
```

---

## Project Structure

```
audex/
├── audex/                 # Main package
│   ├── cli/               # Command-line interface
│   ├── service/           # Business layer
│   ├── entity/            # Entities
│   ├── filters/           # Data filters
│   ├── valueobj/          # Value objects
│   ├── view/              # View layer
│   └── lib/               # Shared libraries
├── packaging/
│   └── linux/             # DEB packaging
│       ├── templates/     # Package templates
│       ├── build.sh       # Build script
│       └── test.sh        # Test script
├── scripts/               # Development scripts
├── tests/                 # Test suite
└── pyproject.toml         # Project configuration
```

---

## Links

- **Documentation**: https://6ixgodd.github.io/audex/
- **PyPI**: https://pypi.org/project/audex/
- **GitHub**: https://github.com/6ixGODD/audex
- **Issues**: https://github.com/6ixGODD/audex/issues
- **Releases**: https://github.com/6ixGODD/audex/releases

---
