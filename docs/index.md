# Audex

Smart Medical Recording & Transcription System with voice recognition and speaker identification.

---

## Requirements

- Python 3.10-3.13
- Poetry
- PortAudio (for audio processing)
- FFmpeg (for audio format conversion)
- PyQt6 (Linux: install from system packages)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev ffmpeg python3-pyqt6 python3-pyqt6.qtwebengine
```

**macOS:**
```bash
brew install portaudio ffmpeg
```

**Windows:**
- PortAudio is bundled with PyAudio wheel
- FFmpeg: Download from https://ffmpeg.org/download.html and add to `PATH`

---

## Development

### Install Dependencies

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

Download from [Releases](https://github.com/6ixGODD/audex/releases):

```bash
sudo dpkg -i audex_{version}_arm64.deb
sudo apt-get install -f
```

**Post-installation:**

```bash
# Run configuration wizard
audex-setup

# Initialize VPR group
audex init vprgroup --config ~/.config/audex/config.yml

# Start application
audex

# (Optional) Enable auto-start
systemctl --user enable audex
systemctl --user start audex
```

---

## DEB Package Development

### Build DEB Package

**Prerequisites:**
- Docker (for cross-platform builds)

**Build:**

```bash
cd packaging/linux

# Build for Raspberry Pi (arm64)
./build.sh

# Build for amd64
./build.sh amd64
```

**Output:** `dist/audex_{version}_{arch}.deb`

### Test DEB Package

```bash
cd packaging/linux
./test.sh
```

**Inside test container:**

```bash
# Install package
sudo dpkg -i /tmp/audex.deb
sudo apt-get install -f

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

### Manual Build (Without Docker)

**On Debian/Ubuntu:**

```bash
cd packaging/linux

# Install build dependencies
sudo apt-get install dpkg-dev

# Build package
python3 build_in_docker.py {version} {arch}

# Example
python3 build_in_docker.py 1.0.1 arm64
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

See `.config.example.yml` for full configuration options.

---

## Project Structure

```
audex/
├── audex/                 # Main package
│   ├── cli/               # CLI
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

- **PyPI**: https://pypi.org/project/audex/
- **Issues**: https://github.com/6ixGODD/audex/issues
- **Releases**: https://github.com/6ixGODD/audex/releases
