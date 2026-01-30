# GUI-ADB

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**基于 PyQt6 的现代化 ADB 图形化工具，让 Android 设备调试更简单高效**

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用说明](#使用说明) • [项目结构](#项目结构)

</div>

---

## 📖 项目简介

GUI-ADB 是一个功能完善的 Android 调试桥（ADB）图形化工具，采用 PyQt6 构建，提供直观易用的界面来管理 Android 设备并执行常用 ADB 操作。无需记忆复杂的命令行参数，通过点击即可完成设备连接、应用安装、文件传输等日常开发任务。

### ✨ 核心特性

- 🎨 **现代化界面**：采用 Fusion 风格主题，支持高 DPI 显示，界面美观易用
- 📱 **多设备支持**：同时管理多台 Android 设备，快速切换操作目标
- 🔗 **无线连接**：支持 USB 和 Wi-Fi 两种连接方式
- 📷 **扫码配对**：Android 11+ 设备可通过扫描二维码快速配对（无需手动输入配对码）
- ⚡ **异步执行**：所有 ADB 命令在后台线程执行，界面流畅不卡顿
- 📦 **开箱即用**：内置 platform-tools，无需单独安装 ADB
- 🎯 **常用功能**：涵盖安装 APK、截图、日志查看、文件传输等日常操作

## 🚀 功能特性

| 功能模块 | 详细说明 |
|---------|---------|
| **设备管理** | 自动检测已连接设备，支持 USB 和无线连接，一键刷新设备列表 |
| **扫码连接** | 电脑显示二维码，手机扫描即可完成配对（Android 11+），支持 mDNS 自动发现设备 |
| **手动连接** | 支持传统的手动输入 IP 和端口进行无线连接 |
| **安装 APK** | 选择本地 APK 文件一键安装到设备，支持覆盖安装 |
| **截图功能** | 快速截取设备屏幕并保存到本地 |
| **日志查看** | 查看设备 Logcat 日志（默认最近 500 行） |
| **设备重启** | 一键重启设备，支持普通重启、进入 Bootloader、Recovery 模式 |
| **文件传输** | 可视化选择文件路径，支持推送文件到设备和从设备拉取文件 |
| **Shell 命令** | 支持执行任意 ADB Shell 命令，满足高级调试需求 |

## 📋 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows 10/11（Linux 和 macOS 理论上也可运行，但主要针对 Windows 优化）
- **ADB**: 项目已内置 `platform-tools`，无需单独安装；若无则从系统 PATH 查找
- **Android 设备**: 需开启 USB 调试（USB 连接）或启用无线调试（Wi-Fi 连接）

## 🔧 快速开始

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/liuhao16/ADB-GUI.git
cd ADB-GUI

# 安装依赖
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

首次运行时会自动检测已连接的设备。如果未检测到设备，程序会提示是否进行无线连接。

## 📱 使用说明

### 连接设备

#### USB 连接
1. 使用 USB 线连接 Android 设备到电脑
2. 在设备上开启「USB 调试」选项
3. 点击「刷新设备」按钮，设备将出现在设备列表中

#### 无线连接（扫码配对，推荐）

适用于 Android 11+ 设备：

1. 确保电脑和手机连接到同一 Wi-Fi 网络
2. 在手机上打开：**设置 → 开发者选项 → 无线调试**
3. 点击「扫码连接」按钮，程序会显示二维码窗口
4. 在手机上选择「使用二维码配对设备」
5. 扫描电脑屏幕上的二维码
6. 程序会自动通过 mDNS 发现设备并完成配对，配对成功后设备将出现在列表中

> **提示**：Windows 系统若无法发现设备，可安装 [Apple Bonjour](https://support.apple.com/kb/DL999) 以支持 mDNS 服务发现。

#### 手动连接

适用于 Android 10 及以下版本或需要手动输入连接信息的情况：

1. 在手机上获取无线调试的 IP 地址和端口（或配对端口）
2. 点击「手动连接」按钮
3. 根据提示输入 IP 地址、端口和配对码（如需要）
4. 点击连接，成功后设备将出现在列表中

### 常用操作

- **安装 APK**：点击「安装 APK」按钮，选择本地 APK 文件即可
- **截图**：点击「截图」按钮，选择保存位置即可
- **查看日志**：点击「Logcat」按钮，查看最近 500 行日志
- **文件传输**：使用「推送文件」和「拉取文件」进行文件传输
- **执行命令**：在 Shell 输入框中输入命令后按回车或点击「执行」按钮

所有操作的输出都会显示在下方的输出框中，包括执行状态和结果信息。

## 📦 打包成可执行文件

使用 PyInstaller 将项目打包为独立的 Windows 可执行文件：

```bash
# 安装打包依赖（如果尚未安装）
pip install pyinstaller

# 打包（在项目根目录执行）
python -m PyInstaller ADB-GUIB.spec
```

打包完成后，可执行文件位于 `dist/ADB-GUI/` 目录中。运行 `ADB-GUI.exe` 即可使用。

> **注意**：打包后的程序为目录模式（onedir），分发时需要将整个 `ADB-GUI` 文件夹一起拷贝。程序已内置 platform-tools，无需额外安装 ADB。

## 📁 项目结构

```
GUI-ADB/
├── main.py                    # 程序入口，初始化应用和主窗口
├── adb_helper.py              # ADB 命令封装，优先使用项目内 platform-tools
├── GUI-ADB.spec               # PyInstaller 打包配置文件
├── app.manifest               # Windows 应用程序清单文件
├── requirements.txt           # Python 依赖列表
├── README.md                  # 项目说明文档
├── adb.ico / adb.png          # 应用程序图标
│
├── core/                      # 核心功能模块
│   ├── __init__.py
│   ├── workers.py             # 后台工作线程封装
│   └── utils.py               # 工具函数（二维码生成、连接判断等）
│
├── ui/                        # 用户界面模块
│   ├── __init__.py
│   ├── main_window.py         # 主窗口类
│   ├── panels.py              # 功能面板组件（设备栏、快捷操作、输出区等）
│   ├── theme.py               # 主题样式定义
│   ├── widgets.py             # 自定义控件
│   └── dialogs/               # 对话框组件
│       ├── __init__.py
│       ├── pairing_dialog.py  # 扫码配对对话框
│       ├── manual_connect_dialog.py  # 手动连接对话框
│       └── device_path_dialog.py     # 设备路径选择对话框
│
└── platform-tools/            # Android SDK platform-tools（内置 ADB）
    ├── adb.exe
    └── ...
```

## 🛠️ 技术栈

- **GUI 框架**: PyQt6 6.6.0+
- **网络发现**: zeroconf（mDNS 服务发现）
- **二维码生成**: qrcode[pil]
- **打包工具**: PyInstaller

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果你有好的想法或发现了问题，请：
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发计划

- [ ] 支持实时 Logcat 日志流
- [ ] 添加录屏功能
- [ ] 支持批量安装 APK
- [ ] 添加常用 Shell 命令预设按钮
- [ ] 支持应用管理（查看已安装应用、卸载等）
- [ ] 添加设备信息查看功能
- [ ] 支持命令历史记录

## 📄 License

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - 强大的 Python GUI 框架
- [Android Debug Bridge](https://developer.android.com/studio/command-line/adb) - Android 官方调试工具
- [zeroconf](https://github.com/python-zeroconf/python-zeroconf) - mDNS 服务发现库

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

Made with ❤️ by [liuhao1]

</div>
