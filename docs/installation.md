# Installation Guide

## Overview

This guide provides detailed instructions for installing Audex from DEB packages on Debian-based Linux distributions.

This project is distributed as DEB packages for AMD64 and ARM64 architectures.

## System Requirements

### Supported Architectures

- `amd64` (`x86_64`)
- `arm64` (`aarch64`)

### Supported Operating Systems

- Debian 11 (Bullseye) or later
- Ubuntu 20.04 LTS or later
- Raspberry Pi OS (64-bit)

### Required Privileges

Audex requires root privileges to run. All installation and runtime operations must be executed with `sudo` or as the root user.

## Installation

### Step 1: Download DEB Package

Download the appropriate DEB package for your system architecture from the GitHub Releases page.

**ARM64:**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_arm64. deb
```

**AMD64:**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_amd64. deb
```

### Step 2: Install Package

Install the downloaded package using `dpkg`:

```bash
sudo dpkg -i audex_{version}_arm64.deb
```

If dependency errors occur during installation, run:

```bash
sudo apt-get install -f
```

### Step 3: Installation Process

The installation process performs the following operations:

1. **Create System Directories**
   - `/etc/audex/` - System configuration directory
   - `/var/lib/audex/` - Application data storage
   - `/var/lib/audex/store/` - Audio file storage
   - `/var/log/audex/` - Application log files
   - `/usr/lib/audex/` - Application installation directory

2. **Setup Python Virtual Environment**
   - Creates Python virtual environment at `/usr/lib/audex/venv`

3. **Install Audex from PyPI**
   - Downloads and installs Audex package and dependencies from Python Package Index

4. **Generate Configuration Files**
   - `/etc/audex/config.system.yml` - System default configuration template
   - `/etc/audex/config.example.yml` - Configuration reference example

5. **Configure Systemd Service**
   - Installs systemd service unit file at `/usr/lib/systemd/system/audex.service`
   - Service is not enabled by default

### Step 4: Verify Installation

Verify the installation was successful:

```bash
# Check installed package version
dpkg -l | grep audex

# Verify executable files
which audex
which audex-setup

# Check systemd service
systemctl status audex.service
```

Expected output:

```
/usr/bin/audex
/usr/bin/audex-setup
```

Inspect installed directory structure:

```bash
# Configuration directory
ls -la /etc/audex/

# Data directory
ls -la /var/lib/audex/

# Log directory
ls -la /var/log/audex/

# Installation directory
tree /usr/lib/audex/
```

## Configuration

### Initial Setup Wizard

After installation, run the interactive setup wizard to configure Audex:

```bash
sudo audex-setup
```

The setup wizard guides you through the following steps:

1. **Load System Configuration**
   - Reads default configuration from `/etc/audex/config. system.yml`

2. **Configure Transcription Provider**
   - Prompts for Dashscope API Key

3. **Configure VPR Provider**
   - Prompts for XFYun App ID, API Key, API Secret

4. **Save Configuration**
   - Writes configuration to `/etc/audex/config.yml`

5. **Initialize VPR Group (Optional)**
   - Creates voice print recognition group
   - Group ID is saved to `/etc/audex/. xf.vprgroup`

### Configuration Files

| File Path | Purpose |
|-----------|---------|
| `/etc/audex/config.yml` | Main configuration file used at runtime (created by setup wizard) |
| `/etc/audex/config. system.yml` | System default configuration template |
| `/etc/audex/config.example.yml` | Complete configuration reference example |
| `/etc/audex/.xf.vprgroup` | XFYun VPR group identifier (auto-generated during setup) |

### Manual Configuration

Manually edit the configuration file:

```bash
sudo nano /etc/audex/config.yml
```

Refer to `/etc/audex/config.example.yml` for all available configuration options.

## Running Audex

### Manual Execution

Start Audex manually:

```bash
sudo audex
```

To stop the application, press `Ctrl+C`.

### Systemd Service

#### Enable Service

Enable automatic startup on boot:

```bash
sudo systemctl enable audex.service
```

#### Start Service

Start the service:

```bash
sudo systemctl start audex.service
```

#### Check Service Status

View service status:

```bash
sudo systemctl status audex.service
```

#### Stop Service

Stop the service:

```bash
sudo systemctl stop audex.service
```

#### Disable Service

Disable automatic startup on boot:

```bash
sudo systemctl disable audex. service
```

#### Restart Service

Restart the service:

```bash
sudo systemctl restart audex.service
```

## Viewing Logs

### Systemd Logs

View real-time service logs:

```bash
sudo journalctl -u audex.service -f
```

View recent logs:

```bash
sudo journalctl -u audex.service -n 100
```

### Application Log Files

View real-time application logs:

```bash
sudo tail -f /var/log/audex/audex.log
```

View recent logs:

```bash
sudo tail -n 50 /var/log/audex/audex.log
```

Search for errors in logs:

```bash
sudo grep -i error /var/log/audex/audex.log
```

## System Directories

| Directory | Purpose | Permissions |
|-----------|---------|-------------|
| `/etc/audex/` | Configuration files | 755 (root:root) |
| `/var/lib/audex/` | Application data and database | 755 (root:root) |
| `/var/lib/audex/store/` | Recorded audio files | 755 (root:root) |
| `/var/log/audex/` | Application log files | 755 (root:root) |
| `/usr/lib/audex/` | Application installation files | 755 (root:root) |
| `/usr/lib/audex/venv/` | Python virtual environment | 755 (root:root) |
| `/usr/bin/audex` | Main executable script | 755 (root:root) |
| `/usr/bin/audex-setup` | Setup wizard script | 755 (root:root) |
| `/usr/lib/systemd/system/audex.service` | Systemd service unit file | 644 (root:root) |

## Uninstallation

### Remove Package (Preserve Configuration)

Remove Audex but keep configuration files:

```bash
sudo apt-get remove audex
```

Preserved directories:
- `/etc/audex/`
- `/var/lib/audex/`
- `/var/log/audex/`

### Complete Removal (Purge)

Remove Audex and all configuration files:

```bash
sudo apt-get purge audex
```

### Manual Cleanup

Manually clean up remaining files if needed:

```bash
sudo rm -rf /etc/audex
sudo rm -rf /var/lib/audex
sudo rm -rf /var/log/audex
sudo rm -rf /usr/lib/audex
```

---

# 安装指南

## 概述

本指南提供在基于 Debian 的 Linux 发行版上从 DEB 包安装 Audex 的详细说明。

本项目基于 DEB 分发，适用于 AMD64 和 ARM64 架构。

## 系统要求

### 支持的架构

- `amd64` (`x86_64`)
- `arm64` (`aarch64`)

### 支持的操作系统

- Debian 11 (Bullseye) 或更高版本
- Ubuntu 20.04 LTS 或更高版本
- Raspberry Pi OS (64 位)

### 所需权限

Audex 需要 root 权限才能运行。所有安装和运行操作都必须使用 `sudo` 或以 root 用户身份执行。

## 安装步骤

### 步骤 1：下载 DEB 包

从 GitHub Releases 页面下载适合您系统架构的 DEB 包。

**ARM64：**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_arm64.deb
```

**AMD64：**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_amd64.deb
```

### 步骤 2：安装软件包

使用 `dpkg` 安装下载的软件包：

```bash
sudo dpkg -i audex_{version}_arm64.deb
```

如果安装过程中出现依赖错误，运行：

```bash
sudo apt-get install -f
```

### 步骤 3：安装过程

安装过程将执行以下操作：

1. **创建系统目录**
   - `/etc/audex/` - 系统配置目录
   - `/var/lib/audex/` - 应用程序数据存储
   - `/var/lib/audex/store/` - 音频文件存储
   - `/var/log/audex/` - 应用程序日志文件
   - `/usr/lib/audex/` - 应用程序安装目录

2. **设置 Python 虚拟环境**
   - 在 `/usr/lib/audex/venv` 创建 Python 虚拟环境

3. **从 PyPI 安装 Audex**
   - 从 Python Package Index 下载并安装 Audex 包及其依赖项

4. **生成配置文件**
   - `/etc/audex/config.system.yml` - 系统默认配置模板
   - `/etc/audex/config.example.yml` - 配置参考示例

5. **配置 Systemd 服务**
   - 在 `/usr/lib/systemd/system/audex.service` 安装 systemd 服务单元文件
   - 服务默认未启用

### 步骤 4：验证安装

验证安装是否成功：

```bash
# 检查已安装的软件包版本
dpkg -l | grep audex

# 验证可执行文件
which audex
which audex-setup

# 检查 systemd 服务
systemctl status audex. service
```

预期输出：

```
/usr/bin/audex
/usr/bin/audex-setup
```

检查已安装的目录结构：

```bash
# 配置目录
ls -la /etc/audex/

# 数据目录
ls -la /var/lib/audex/

# 日志目录
ls -la /var/log/audex/

# 安装目录
tree /usr/lib/audex/
```

## 配置

### 初始化设置向导

安装后，运行交互式设置向导配置 Audex：

```bash
sudo audex-setup
```

设置向导将引导您完成以下步骤：

1. **加载系统配置**
   - 从 `/etc/audex/config. system.yml` 读取默认配置

2. **配置转录服务提供商**
   - 提示输入 Dashscope API Key

3. **配置声纹识别提供商**
   - 提示输入 XFYun App ID、API Key、API Secret

4. **保存配置**
   - 将配置写入 `/etc/audex/config.yml`

5. **初始化 VPR 组（可选）**
   - 创建声纹识别组
   - 组 ID 保存到 `/etc/audex/.xf.vprgroup`

### 配置文件

| 文件路径 | 用途 |
|---------|------|
| `/etc/audex/config.yml` | 运行时使用的主配置文件（由设置向导创建）|
| `/etc/audex/config.system.yml` | 系统默认配置模板 |
| `/etc/audex/config.example.yml` | 完整的配置参考示例 |
| `/etc/audex/. xf.vprgroup` | 讯飞 VPR 组标识符（设置时自动生成）|

### 手动配置

手动编辑配置文件：

```bash
sudo nano /etc/audex/config.yml
```

参考 `/etc/audex/config.example.yml` 获取所有可用的配置选项。

## 运行 Audex

### 手动执行

手动启动 Audex：

```bash
sudo audex
```

停止应用程序，按 `Ctrl+C`。

### Systemd 服务

#### 启用服务

启用开机自动启动：

```bash
sudo systemctl enable audex.service
```

#### 启动服务

启动服务：

```bash
sudo systemctl start audex.service
```

#### 检查服务状态

查看服务状态：

```bash
sudo systemctl status audex.service
```

#### 停止服务

停止服务：

```bash
sudo systemctl stop audex.service
```

#### 禁用服务

禁用开机自动启动：

```bash
sudo systemctl disable audex. service
```

#### 重启服务

重启服务：

```bash
sudo systemctl restart audex.service
```

## 查看日志

### Systemd 日志

查看实时服务日志：

```bash
sudo journalctl -u audex.service -f
```

查看最近的日志：

```bash
sudo journalctl -u audex.service -n 100
```

### 应用程序日志文件

查看实时应用程序日志：

```bash
sudo tail -f /var/log/audex/audex. log
```

查看最近的日志：

```bash
sudo tail -n 50 /var/log/audex/audex.log
```

搜索错误日志：

```bash
sudo grep -i error /var/log/audex/audex.log
```

## 系统目录

| 目录 | 用途 | 权限 |
|------|------|------|
| `/etc/audex/` | 配置文件 | 755 (root:root) |
| `/var/lib/audex/` | 应用程序数据和数据库 | 755 (root:root) |
| `/var/lib/audex/store/` | 录制的音频文件 | 755 (root:root) |
| `/var/log/audex/` | 应用程序日志文件 | 755 (root:root) |
| `/usr/lib/audex/` | 应用程序安装文件 | 755 (root:root) |
| `/usr/lib/audex/venv/` | Python 虚拟环境 | 755 (root:root) |
| `/usr/bin/audex` | 主可执行脚本 | 755 (root:root) |
| `/usr/bin/audex-setup` | 设置向导脚本 | 755 (root:root) |
| `/usr/lib/systemd/system/audex.service` | Systemd 服务单元文件 | 644 (root:root) |

## 卸载

### 移除软件包（保留配置）

移除 Audex 但保留配置文件：

```bash
sudo apt-get remove audex
```

保留的目录：
- `/etc/audex/`
- `/var/lib/audex/`
- `/var/log/audex/`

### 完全移除（清除）

移除 Audex 及所有配置文件：

```bash
sudo apt-get purge audex
```

### 手动清理

如需手动清理残留文件：

```bash
sudo rm -rf /etc/audex
sudo rm -rf /var/lib/audex
sudo rm -rf /var/log/audex
sudo rm -rf /usr/lib/audex
```
