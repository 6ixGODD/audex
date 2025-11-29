# DEB Package Installation Guide

This guide provides detailed instructions for installing Audex via DEB package on Debian-based Linux systems.

## Overview

Audex is a smart medical recording and transcription system with voice recognition and speaker identification. The DEB package provides a complete system-level installation with systemd service integration, automated configuration, and proper system directory structure.

**Supported Systems:**

- Debian 11+ (Bullseye)
- Ubuntu 20.04+ (Focal Fossa)
- Raspberry Pi OS (64-bit)

## System Requirements

### Supported Architectures

| Architecture | Description |
|-------------|-------------|
| `amd64` | 64-bit x86 systems (Intel/AMD) |
| `arm64` | 64-bit ARM systems (Raspberry Pi 4/5) |

### Supported Operating Systems

- Debian 11 (Bullseye) or later
- Ubuntu 20.04 (Focal Fossa) or later
- Raspberry Pi OS (64-bit, Bookworm recommended)

### Prerequisites

- Python 3.10 or later
- Root or sudo privileges
- Network connection (for PyPI installation during setup)
- System dependencies: `portaudio19-dev`, `ffmpeg`, `python3-pyqt6`, `python3-pyqt6.qtwebengine`

## Installation

### Step 1: Download DEB Package

Download the appropriate DEB package for your architecture from the [GitHub Releases](https://github.com/6ixGODD/audex/releases) page.

**For arm64 (Raspberry Pi):**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v1.0.5/audex_1.0.5_arm64.deb
```

**For amd64 (x86_64):**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v1.0.5/audex_1.0.5_amd64.deb
```

### Step 2: Install Package

Install the DEB package using `dpkg`:

```bash
sudo dpkg -i audex_1.0.5_arm64.deb
```

If there are missing dependencies, resolve them with:

```bash
sudo apt-get install -f
```

### Step 3: Installation Process

During installation, the package performs the following operations:

1. **Create System Directories**
   - `/etc/audex/` - Configuration files
   - `/var/lib/audex/` - Application data and storage
   - `/var/log/audex/` - Log files

2. **Set Up Python Virtual Environment**
   - Creates isolated Python environment at `/usr/lib/audex/venv`
   - Uses system site-packages for PyQt6 integration

3. **Install from PyPI**
   - Downloads and installs the Audex package from PyPI
   - Installs all Python dependencies automatically

4. **Generate Configuration Templates**
   - Creates `/etc/audex/config.system.yml` (system defaults)
   - Creates `/etc/audex/config.example.yml` (configuration reference)

5. **Configure systemd Service**
   - Installs `audex.service` unit file
   - Reloads systemd daemon

### Step 4: Verify Installation

Check installed package version:

```bash
dpkg -l | grep audex
```

Verify executable location:

```bash
which audex
```

Expected output: `/usr/bin/audex`

Check directory structure:

```bash
ls -la /etc/audex/
ls -la /var/lib/audex/
ls -la /var/log/audex/
```

## Configuration

### Initial Setup Wizard

Run the interactive setup wizard to configure Audex:

```bash
sudo audex-setup
```

The setup wizard will guide you through:

1. **Transcription Service Configuration**
   - Dashscope API Key (required for speech-to-text)

2. **Voice Print Recognition (VPR) Configuration**
   - XFYun App ID
   - XFYun API Key
   - XFYun API Secret

3. **VPR Group Initialization**
   - Creates voice print recognition group
   - Stores group ID for speaker identification

### Configuration Files

| File | Description |
|------|-------------|
| `/etc/audex/config.yml` | Active configuration (created by setup wizard) |
| `/etc/audex/config.system.yml` | System default values |
| `/etc/audex/config.example.yml` | Configuration reference template |
| `/etc/audex/.xf.vprgroup` | VPR group ID (auto-generated) |

### Manual Configuration

To manually edit the configuration:

```bash
sudo nano /etc/audex/config.yml
```

You can copy the example configuration as a starting point:

```bash
sudo cp /etc/audex/config.example.yml /etc/audex/config.yml
```

Edit the file to add your API credentials and customize settings.

## Running Audex

### Manual Execution

Start Audex manually (requires root privileges):

```bash
sudo audex
```

To stop Audex when running manually, press `Ctrl+C` or close the terminal.

### Systemd Service

**Enable service to start on boot:**

```bash
sudo systemctl enable audex.service
```

**Start service:**

```bash
sudo systemctl start audex.service
```

**Check service status:**

```bash
sudo systemctl status audex.service
```

**Stop service:**

```bash
sudo systemctl stop audex.service
```

**Disable auto-start on boot:**

```bash
sudo systemctl disable audex.service
```

### Auto-start on Boot

To configure Audex to start automatically when the system boots:

```bash
sudo systemctl enable audex.service
sudo systemctl start audex.service
```

The service will now start automatically after each reboot.

## Viewing Logs

### Systemd Journal

View real-time logs from the systemd service:

```bash
sudo journalctl -u audex.service -f
```

View recent logs:

```bash
sudo journalctl -u audex.service -n 100
```

### Application Logs

View application log file:

```bash
sudo tail -f /var/log/audex/audex.log
```

View all log files:

```bash
ls -la /var/log/audex/
```

## System Directories

| Directory | Description |
|-----------|-------------|
| `/etc/audex/` | Configuration files |
| `/var/lib/audex/` | Application data and file storage |
| `/var/log/audex/` | Log files |
| `/usr/lib/audex/` | Python virtual environment and installation |
| `/usr/bin/audex` | Main executable |
| `/usr/bin/audex-setup` | Setup wizard executable |

## Uninstallation

### Remove Package (Keep Configuration)

To remove Audex while preserving configuration files:

```bash
sudo apt-get remove audex
```

### Remove Package and Configuration

To completely remove Audex including all configuration files:

```bash
sudo apt-get purge audex
```

### Manual Cleanup

If needed, manually remove remaining directories:

```bash
sudo rm -rf /etc/audex
sudo rm -rf /var/lib/audex
sudo rm -rf /var/log/audex
sudo rm -rf /usr/lib/audex
```

## Troubleshooting

### Permission Denied Errors

**Symptom:** Error message indicating permission denied when running Audex.

**Solution:** Audex requires root privileges. Always use `sudo`:

```bash
sudo audex
```

Or run via systemd service:

```bash
sudo systemctl start audex.service
```

### Systemd Service Does Not Start

**Symptom:** Service fails to start or crashes immediately.

**Solution:**

1. Check service status for error messages:

   ```bash
   sudo systemctl status audex.service
   ```

2. View detailed logs:

   ```bash
   sudo journalctl -u audex.service -n 50
   ```

3. Verify configuration file exists and is valid:

   ```bash
   sudo cat /etc/audex/config.yml
   ```

4. Run setup wizard if configuration is missing:

   ```bash
   sudo audex-setup
   ```

### Configuration Errors

**Symptom:** Audex fails to start with configuration-related error.

**Solution:**

1. Verify configuration file syntax:

   ```bash
   sudo cat /etc/audex/config.yml
   ```

2. Check for placeholder values (e.g., `<UNSET>`):

   ```bash
   grep "<UNSET>" /etc/audex/config.yml
   ```

3. Re-run setup wizard to reconfigure:

   ```bash
   sudo audex-setup
   ```

### Dependency Issues

**Symptom:** Package installation fails due to missing dependencies.

**Solution:**

1. Update package lists:

   ```bash
   sudo apt-get update
   ```

2. Install missing dependencies:

   ```bash
   sudo apt-get install -f
   ```

3. Install system dependencies manually if needed:

   ```bash
   sudo apt-get install portaudio19-dev ffmpeg python3-pyqt6 python3-pyqt6.qtwebengine
   ```

4. Reinstall the package:

   ```bash
   sudo dpkg -i audex_1.0.5_arm64.deb
   sudo apt-get install -f
   ```

---

# DEB 包安装指南

本指南提供在基于 Debian 的 Linux 系统上通过 DEB 包安装 Audex 的详细说明。

## 概述

Audex 是一款智能医疗录音与转录系统，具备语音识别和说话人识别功能。DEB 包提供完整的系统级安装，包括 systemd 服务集成、自动化配置和规范的系统目录结构。

**适用系统：**

- Debian 11+ (Bullseye)
- Ubuntu 20.04+ (Focal Fossa)
- Raspberry Pi OS（64 位）

## 系统要求

### 支持架构

| 架构 | 描述 |
|------|------|
| `amd64` | 64 位 x86 系统（Intel/AMD） |
| `arm64` | 64 位 ARM 系统（Raspberry Pi 4/5） |

### 支持操作系统

- Debian 11 (Bullseye) 或更高版本
- Ubuntu 20.04 (Focal Fossa) 或更高版本
- Raspberry Pi OS（64 位，推荐 Bookworm）

### 前置条件

- Python 3.10 或更高版本
- Root 或 sudo 权限
- 网络连接（安装过程中需要从 PyPI 下载依赖）
- 系统依赖：`portaudio19-dev`、`ffmpeg`、`python3-pyqt6`、`python3-pyqt6.qtwebengine`

## 安装步骤

### 步骤 1：下载 DEB 包

从 [GitHub Releases](https://github.com/6ixGODD/audex/releases) 页面下载适合您架构的 DEB 包。

**arm64（Raspberry Pi）：**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v1.0.5/audex_1.0.5_arm64.deb
```

**amd64（x86_64）：**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v1.0.5/audex_1.0.5_amd64.deb
```

### 步骤 2：安装软件包

使用 `dpkg` 安装 DEB 包：

```bash
sudo dpkg -i audex_1.0.5_arm64.deb
```

如果存在缺失的依赖项，使用以下命令解决：

```bash
sudo apt-get install -f
```

### 步骤 3：安装过程

安装过程中，软件包会执行以下操作：

1. **创建系统目录**
   - `/etc/audex/` - 配置文件
   - `/var/lib/audex/` - 应用数据和存储
   - `/var/log/audex/` - 日志文件

2. **设置 Python 虚拟环境**
   - 在 `/usr/lib/audex/venv` 创建隔离的 Python 环境
   - 使用系统 site-packages 以支持 PyQt6

3. **从 PyPI 安装**
   - 从 PyPI 下载并安装 Audex 包
   - 自动安装所有 Python 依赖

4. **生成配置模板**
   - 创建 `/etc/audex/config.system.yml`（系统默认值）
   - 创建 `/etc/audex/config.example.yml`（配置参考）

5. **配置 systemd 服务**
   - 安装 `audex.service` 单元文件
   - 重新加载 systemd 守护进程

### 步骤 4：验证安装

检查已安装的软件包版本：

```bash
dpkg -l | grep audex
```

验证可执行文件位置：

```bash
which audex
```

预期输出：`/usr/bin/audex`

检查目录结构：

```bash
ls -la /etc/audex/
ls -la /var/lib/audex/
ls -la /var/log/audex/
```

## 配置

### 初始化设置向导

运行交互式设置向导配置 Audex：

```bash
sudo audex-setup
```

设置向导将引导您完成以下配置：

1. **转录服务配置**
   - Dashscope API Key（语音转文字所需）

2. **声纹识别（VPR）配置**
   - XFYun App ID
   - XFYun API Key
   - XFYun API Secret

3. **VPR 组初始化**
   - 创建声纹识别组
   - 存储用于说话人识别的组 ID

### 配置文件

| 文件 | 描述 |
|------|------|
| `/etc/audex/config.yml` | 活动配置（由设置向导创建） |
| `/etc/audex/config.system.yml` | 系统默认值 |
| `/etc/audex/config.example.yml` | 配置参考模板 |
| `/etc/audex/.xf.vprgroup` | VPR 组 ID（自动生成） |

### 手动配置

手动编辑配置文件：

```bash
sudo nano /etc/audex/config.yml
```

您可以复制示例配置作为起点：

```bash
sudo cp /etc/audex/config.example.yml /etc/audex/config.yml
```

编辑文件以添加您的 API 凭证并自定义设置。

## 运行 Audex

### 手动执行

手动启动 Audex（需要 root 权限）：

```bash
sudo audex
```

手动运行时停止 Audex，按 `Ctrl+C` 或关闭终端。

### Systemd 服务

**启用服务开机自启：**

```bash
sudo systemctl enable audex.service
```

**启动服务：**

```bash
sudo systemctl start audex.service
```

**检查服务状态：**

```bash
sudo systemctl status audex.service
```

**停止服务：**

```bash
sudo systemctl stop audex.service
```

**禁用开机自启：**

```bash
sudo systemctl disable audex.service
```

### 开机自启动

配置 Audex 在系统启动时自动启动：

```bash
sudo systemctl enable audex.service
sudo systemctl start audex.service
```

服务将在每次重启后自动启动。

## 查看日志

### 系统日志

实时查看 systemd 服务日志：

```bash
sudo journalctl -u audex.service -f
```

查看最近日志：

```bash
sudo journalctl -u audex.service -n 100
```

### 应用日志

查看应用日志文件：

```bash
sudo tail -f /var/log/audex/audex.log
```

查看所有日志文件：

```bash
ls -la /var/log/audex/
```

## 系统目录

| 目录 | 描述 |
|------|------|
| `/etc/audex/` | 配置文件 |
| `/var/lib/audex/` | 应用数据和文件存储 |
| `/var/log/audex/` | 日志文件 |
| `/usr/lib/audex/` | Python 虚拟环境和安装文件 |
| `/usr/bin/audex` | 主可执行文件 |
| `/usr/bin/audex-setup` | 设置向导可执行文件 |

## 卸载

### 卸载软件包（保留配置）

卸载 Audex 但保留配置文件：

```bash
sudo apt-get remove audex
```

### 卸载软件包和配置

完全卸载 Audex，包括所有配置文件：

```bash
sudo apt-get purge audex
```

### 手动清理

如需手动删除剩余目录：

```bash
sudo rm -rf /etc/audex
sudo rm -rf /var/lib/audex
sudo rm -rf /var/log/audex
sudo rm -rf /usr/lib/audex
```

## 故障排除

### 权限拒绝错误

**症状：** 运行 Audex 时出现权限拒绝错误信息。

**解决方案：** Audex 需要 root 权限，请始终使用 `sudo`：

```bash
sudo audex
```

或通过 systemd 服务运行：

```bash
sudo systemctl start audex.service
```

### Systemd 服务无法启动

**症状：** 服务无法启动或立即崩溃。

**解决方案：**

1. 检查服务状态获取错误信息：

   ```bash
   sudo systemctl status audex.service
   ```

2. 查看详细日志：

   ```bash
   sudo journalctl -u audex.service -n 50
   ```

3. 验证配置文件存在且有效：

   ```bash
   sudo cat /etc/audex/config.yml
   ```

4. 如配置缺失，运行设置向导：

   ```bash
   sudo audex-setup
   ```

### 配置错误

**症状：** Audex 因配置相关错误无法启动。

**解决方案：**

1. 验证配置文件语法：

   ```bash
   sudo cat /etc/audex/config.yml
   ```

2. 检查占位符值（如 `<UNSET>`）：

   ```bash
   grep "<UNSET>" /etc/audex/config.yml
   ```

3. 重新运行设置向导进行配置：

   ```bash
   sudo audex-setup
   ```

### 依赖问题

**症状：** 因缺少依赖项导致软件包安装失败。

**解决方案：**

1. 更新软件包列表：

   ```bash
   sudo apt-get update
   ```

2. 安装缺失的依赖项：

   ```bash
   sudo apt-get install -f
   ```

3. 如需手动安装系统依赖：

   ```bash
   sudo apt-get install portaudio19-dev ffmpeg python3-pyqt6 python3-pyqt6.qtwebengine
   ```

4. 重新安装软件包：

   ```bash
   sudo dpkg -i audex_1.0.5_arm64.deb
   sudo apt-get install -f
   ```
