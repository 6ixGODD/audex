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

Audex runs as a **normal user** (not root). Installation requires root privileges, but runtime operations are executed as your regular user account.

## Installation

### Step 1: Download DEB Package

Download the appropriate DEB package for your system architecture from the GitHub Releases page.

**ARM64:**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_arm64.deb
```

**AMD64:**

```bash
wget https://github.com/6ixGODD/audex/releases/download/v{version}/audex_{version}_amd64.deb
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
   - `/opt/audex/` - Application installation directory
   - `/etc/audex/templates/` - Configuration templates
   - `/etc/audex/systemd/` - User systemd service template

2. **Setup Python Virtual Environment**
   - Creates Python virtual environment at `/opt/audex/venv`

3. **Install Audex from PyPI**
   - Downloads and installs Audex package and dependencies from Python Package Index

4. **Generate Configuration Templates**
   - `/etc/audex/templates/config.system.yml` - System default configuration template
   - `/etc/audex/templates/config.example.yml` - Configuration reference example

5. **Prepare User Directories**
   - Creates directory structure for existing users:
     - `~/.config/audex/` - User configuration
     - `~/.local/share/audex/store/` - Audio file storage
     - `~/.local/share/audex/logs/` - Application log files

6. **Update Desktop Integration**
   - Installs desktop entry at `/usr/share/applications/audex.desktop`
   - Installs application icon
   - Updates desktop database and icon cache

### Step 4: Verify Installation

Verify the installation was successful:

```bash
# Check installed package version
dpkg -l | grep audex

# Verify executable files
which audex
which audex-setup
which audex-enable-service

# Check desktop file
ls -la /usr/share/applications/audex.desktop

# Check icon
ls -la /usr/share/pixmaps/audex.svg
```

Expected output:

```
/usr/bin/audex
/usr/bin/audex-setup
/usr/bin/audex-enable-service
```

Inspect installed directory structure:

```bash
# Configuration templates
ls -la /etc/audex/templates/

# Service template
ls -la /etc/audex/systemd/

# Installation directory
ls -la /opt/audex/
```

## Configuration

### Initial Setup Wizard

After installation, run the interactive setup wizard to configure Audex (as your normal user, **not root**):

```bash
audex-setup
```

The setup wizard guides you through the following steps:

1. **Check Existing Configuration**
   - If configuration exists, offers options to edit or overwrite

2. **Load Configuration Template**
   - Reads default configuration from `/etc/audex/templates/config.system.yml`
   - Expands environment variables (e.g., `${HOME}`)

3. **Audio Device Detection**
   - Detects available input devices on your system

4. **Configure Transcription Provider**
   - Prompts for Dashscope API Key

5. **Configure VPR Provider**
   - Prompts for XFYun App ID, API Key, API Secret

6. **Save Configuration**
   - Writes configuration to `~/.config/audex/config.yml`

7. **Initialize VPR Group (Optional)**
   - Creates voice print recognition group
   - Group ID is saved to `~/.config/audex/.xf.vprgroup`

### Configuration Files

| File Path | Purpose |
|-----------|---------|
| `~/.config/audex/config.yml` | Main configuration file used at runtime (created by setup wizard) |
| `/etc/audex/templates/config.system.yml` | System default configuration template |
| `/etc/audex/templates/config.example.yml` | Complete configuration reference example |
| `~/.config/audex/.xf.vprgroup` | XFYun VPR group identifier (auto-generated during setup) |

### Manual Configuration

Manually edit your configuration file:

```bash
nano ~/.config/audex/config.yml
```

Refer to `/etc/audex/templates/config.example.yml` for all available configuration options.

## Running Audex

### From Application Menu

After installation, Audex appears in your application menu under **AudioVideo** > **Audex**.

### Manual Execution

Start Audex manually from command line:

```bash
audex
```

To stop the application, press `Ctrl+C` or close the window.

### User Systemd Service (Recommended for Auto-Start)

#### Enable Auto-Start Service

To enable Audex to start automatically on boot:

```bash
audex-enable-service
```

This command:
- Installs user systemd service from template
- Enables the service for your user
- Enables `linger` for boot persistence
- Starts the service immediately

#### Manual Service Management

If you prefer to manage the service manually:

```bash
# Start service
systemctl --user start audex.service

# Stop service
systemctl --user stop audex.service

# Restart service
systemctl --user restart audex.service

# Enable auto-start
systemctl --user enable audex.service
sudo loginctl enable-linger $USER

# Disable auto-start
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# Check service status
systemctl --user status audex.service
```

## Viewing Logs

### User Systemd Logs

View real-time service logs:

```bash
journalctl --user -u audex.service -f
```

View recent logs:

```bash
journalctl --user -u audex.service -n 100
```

### Application Log Files

View real-time application logs:

```bash
tail -f ~/.local/share/audex/logs/audex.log
```

View recent logs:

```bash
tail -n 50 ~/.local/share/audex/logs/audex.log
```

Search for errors in logs:

```bash
grep -i error ~/.local/share/audex/logs/audex.log
```

## System and User Directories

### System Directories

| Directory | Purpose | Permissions |
|-----------|---------|-------------|
| `/opt/audex/` | Application installation files | 755 (root:root) |
| `/opt/audex/venv/` | Python virtual environment | 755 (root:root) |
| `/etc/audex/templates/` | Configuration templates | 755 (root:root) |
| `/etc/audex/systemd/` | User systemd service template | 755 (root:root) |
| `/usr/bin/audex` | Main executable script | 755 (root:root) |
| `/usr/bin/audex-setup` | Setup wizard script | 755 (root:root) |
| `/usr/bin/audex-enable-service` | Service installer script | 755 (root:root) |
| `/usr/share/applications/audex.desktop` | Desktop entry file | 644 (root:root) |
| `/usr/share/pixmaps/audex.svg` | Application icon | 644 (root:root) |

### User Directories

| Directory | Purpose | Permissions |
|-----------|---------|-------------|
| `~/.config/audex/` | User configuration files | 755 (user:user) |
| `~/.local/share/audex/` | Application data and database | 755 (user:user) |
| `~/.local/share/audex/store/` | Recorded audio files | 755 (user:user) |
| `~/.local/share/audex/logs/` | Application log files | 755 (user:user) |
| `~/.config/systemd/user/audex.service` | User systemd service (after running audex-enable-service) | 644 (user:user) |

## Uninstallation

### Remove Package (Preserve User Data)

Remove Audex but keep user configuration and data:

```bash
# Disable service first (if enabled)
systemctl --user stop audex.service
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# Remove package
sudo apt-get remove audex
```

Preserved user directories:
- `~/.config/audex/`
- `~/.local/share/audex/`

### Complete Removal (Purge)

Remove Audex and all system files:

```bash
# Disable service first (if enabled)
systemctl --user stop audex.service
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# Purge package
sudo apt-get purge audex

# Manually remove user data (optional)
rm -rf ~/.config/audex
rm -rf ~/.local/share/audex
rm -rf ~/.config/systemd/user/audex.service
```

---

# 安装指南

## 概述

本指南提供在基于 Debian 的 Linux 发行版上从 DEB 包安装 Audex 的详细说明。

本项目基于 DEB 分发,适用于 AMD64 和 ARM64 架构。

## 系统要求

### 支持的架构

- `amd64` (`x86_64`)
- `arm64` (`aarch64`)

### 支持的操作系统

- Debian 11 (Bullseye) 或更高版本
- Ubuntu 20.04 LTS 或更高版本
- Raspberry Pi OS (64 位)

### 所需权限

Audex 以**普通用户**身份运行（非 root）。安装需要 root 权限，但运行时操作以常规用户帐户执行。

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
   - `/opt/audex/` - 应用程序安装目录
   - `/etc/audex/templates/` - 配置模板
   - `/etc/audex/systemd/` - 用户 systemd 服务模板

2. **设置 Python 虚拟环境**
   - 在 `/opt/audex/venv` 创建 Python 虚拟环境

3. **从 PyPI 安装 Audex**
   - 从 Python Package Index 下载并安装 Audex 包及其依赖项

4. **生成配置模板**
   - `/etc/audex/templates/config.system.yml` - 系统默认配置模板
   - `/etc/audex/templates/config.example.yml` - 配置参考示例

5. **准备用户目录**
   - 为现有用户创建目录结构：
     - `~/.config/audex/` - 用户配置
     - `~/.local/share/audex/store/` - 音频文件存储
     - `~/.local/share/audex/logs/` - 应用程序日志文件

6. **更新桌面集成**
   - 在 `/usr/share/applications/audex.desktop` 安装桌面条目
   - 安装应用程序图标
   - 更新桌面数据库和图标缓存

### 步骤 4：验证安装

验证安装是否成功：

```bash
# 检查已安装的软件包版本
dpkg -l | grep audex

# 验证可执行文件
which audex
which audex-setup
which audex-enable-service

# 检查桌面文件
ls -la /usr/share/applications/audex.desktop

# 检查图标
ls -la /usr/share/pixmaps/audex.svg
```

预期输出：

```
/usr/bin/audex
/usr/bin/audex-setup
/usr/bin/audex-enable-service
```

检查已安装的目录结构：

```bash
# 配置模板
ls -la /etc/audex/templates/

# 服务模板
ls -la /etc/audex/systemd/

# 安装目录
ls -la /opt/audex/
```

## 配置

### 初始化设置向导

安装后，运行交互式设置向导配置 Audex（以普通用户身份，**非 root**）：

```bash
audex-setup
```

设置向导将引导您完成以下步骤：

1. **检查现有配置**
   - 如果配置存在，提供编辑或覆盖选项

2. **加载配置模板**
   - 从 `/etc/audex/templates/config.system.yml` 读取默认配置
   - 展开环境变量（例如 `${HOME}`）

3. **音频设备检测**
   - 检测系统上可用的输入设备

4. **配置转录服务提供商**
   - 提示输入 Dashscope API Key

5. **配置声纹识别提供商**
   - 提示输入 XFYun App ID、API Key、API Secret

6.  **保存配置**
   - 将配置写入 `~/.config/audex/config.yml`

7. **初始化 VPR 组（可选）**
   - 创建声纹识别组
   - 组 ID 保存到 `~/.config/audex/.xf.vprgroup`

### 配置文件

| 文件路径 | 用途 |
|---------|------|
| `~/.config/audex/config.yml` | 运行时使用的主配置文件（由设置向导创建）|
| `/etc/audex/templates/config.system.yml` | 系统默认配置模板 |
| `/etc/audex/templates/config.example.yml` | 完整的配置参考示例 |
| `~/.config/audex/.xf.vprgroup` | 讯飞 VPR 组标识符（设置时自动生成）|

### 手动配置

手动编辑您的配置文件：

```bash
nano ~/.config/audex/config.yml
```

参考 `/etc/audex/templates/config.example.yml` 获取所有可用的配置选项。

## 运行 Audex

### 从应用程序菜单

安装后，Audex 出现在应用程序菜单的 **音频视频** > **Audex** 下。

### 手动执行

从命令行手动启动 Audex：

```bash
audex
```

停止应用程序，按 `Ctrl+C` 或关闭窗口。

### 用户 Systemd 服务（推荐用于自动启动）

#### 启用自动启动服务

要启用 Audex 在开机时自动启动：

```bash
audex-enable-service
```

此命令：
- 从模板安装用户 systemd 服务
- 为您的用户启用服务
- 启用 `linger` 以实现开机持久性
- 立即启动服务

#### 手动服务管理

如果您希望手动管理服务：

```bash
# 启动服务
systemctl --user start audex.service

# 停止服务
systemctl --user stop audex.service

# 重启服务
systemctl --user restart audex.service

# 启用自动启动
systemctl --user enable audex.service
sudo loginctl enable-linger $USER

# 禁用自动启动
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# 检查服务状态
systemctl --user status audex.service
```

## 查看日志

### 用户 Systemd 日志

查看实时服务日志：

```bash
journalctl --user -u audex.service -f
```

查看最近的日志：

```bash
journalctl --user -u audex.service -n 100
```

### 应用程序日志文件

查看实时应用程序日志：

```bash
tail -f ~/.local/share/audex/logs/audex.log
```

查看最近的日志：

```bash
tail -n 50 ~/.local/share/audex/logs/audex.log
```

搜索错误日志：

```bash
grep -i error ~/.local/share/audex/logs/audex.log
```

## 系统和用户目录

### 系统目录

| 目录 | 用途 | 权限 |
|------|------|------|
| `/opt/audex/` | 应用程序安装文件 | 755 (root:root) |
| `/opt/audex/venv/` | Python 虚拟环境 | 755 (root:root) |
| `/etc/audex/templates/` | 配置模板 | 755 (root:root) |
| `/etc/audex/systemd/` | 用户 systemd 服务模板 | 755 (root:root) |
| `/usr/bin/audex` | 主可执行脚本 | 755 (root:root) |
| `/usr/bin/audex-setup` | 设置向导脚本 | 755 (root:root) |
| `/usr/bin/audex-enable-service` | 服务安装脚本 | 755 (root:root) |
| `/usr/share/applications/audex.desktop` | 桌面条目文件 | 644 (root:root) |
| `/usr/share/pixmaps/audex.svg` | 应用程序图标 | 644 (root:root) |

### 用户目录

| 目录 | 用途 | 权限 |
|------|------|------|
| `~/.config/audex/` | 用户配置文件 | 755 (user:user) |
| `~/.local/share/audex/` | 应用程序数据和数据库 | 755 (user:user) |
| `~/.local/share/audex/store/` | 录制的音频文件 | 755 (user:user) |
| `~/.local/share/audex/logs/` | 应用程序日志文件 | 755 (user:user) |
| `~/.config/systemd/user/audex.service` | 用户 systemd 服务（运行 audex-enable-service 后）| 644 (user:user) |

## 卸载

### 移除软件包（保留用户数据）

移除 Audex 但保留用户配置和数据：

```bash
# 首先禁用服务（如果已启用）
systemctl --user stop audex.service
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# 移除软件包
sudo apt-get remove audex
```

保留的用户目录：
- `~/.config/audex/`
- `~/.local/share/audex/`

### 完全移除（清除）

移除 Audex 及所有系统文件：

```bash
# 首先禁用服务（如果已启用）
systemctl --user stop audex.service
systemctl --user disable audex.service
sudo loginctl disable-linger $USER

# 清除软件包
sudo apt-get purge audex

# 手动删除用户数据（可选）
rm -rf ~/.config/audex
rm -rf ~/.local/share/audex
rm -rf ~/.config/systemd/user/audex.service
```
