# ADB 快捷操作 (PyQt6)

基于 PyQt6 的 ADB 图形化快捷操作工具，用于连接 Android 设备并执行常用 ADB 命令。

## 环境要求

- Python 3.10+
- ADB：程序会**优先使用项目内 `platform-tools` 目录下的 adb**（已包含可直接使用）；若无则从系统 PATH 查找
- 设备开启 USB 调试（或已通过 `adb connect` 连接无线设备）

## 安装与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

## 功能说明

| 功能       | 说明                           |
|------------|--------------------------------|
| 设备选择   | 下拉框选择当前操作的设备，支持多设备 |
| 刷新设备   | 重新扫描已连接设备             |
| **扫码连接** | 电脑显示二维码，手机打开「无线调试 → 使用二维码配对设备」扫描后自动配对（Android 11+） |
| 安装 APK   | 选择本地 APK 安装到设备        |
| 截图       | 设备截屏并保存到本地           |
| Logcat     | 查看最近 500 行日志            |
| 重启       | 重启当前设备                   |
| 推送文件   | 将本地文件推送到设备 /sdcard/  |
| 拉取文件   | 从设备指定路径拉取到本地       |
| 自定义 Shell | 输入任意 `adb shell` 命令执行  |

所有命令在后台线程执行，输出会显示在下方输出框中，不会卡住界面。

### 扫码连接说明（手机扫电脑）

1. 电脑与手机处于同一 Wi-Fi。
2. 点击「扫码连接」，程序会弹出窗口并显示二维码。
3. 在手机上打开：**设置 → 开发者选项 → 无线调试 → 使用二维码配对设备**。
4. 用手机扫描电脑屏幕上的二维码。
5. 扫描后程序通过 mDNS 发现设备并自动执行 `adb pair`，配对成功后刷新设备列表。
- **依赖**：`zeroconf`（mDNS）、`qrcode`（生成二维码）。Windows 若无法发现设备，可安装 [Bonjour](https://support.apple.com/kb/DL999) 以支持 mDNS。

## 项目结构

```
GUI-ADB/
├── main.py           # PyQt6 主界面与快捷操作
├── adb_helper.py     # ADB 命令封装（优先使用本目录下 platform-tools/adb）
├── platform-tools/   # Android SDK platform-tools（内含 adb.exe 等）
├── requirements.txt
└── README.md
```

## 扩展建议

- 在 `adb_helper.py` 中增加更多 ADB 封装（如 `logcat -f` 实时日志、录屏等）
- 在 `main.py` 中为常用 Shell 命令增加预设按钮（如「列出包名」「清除数据」等）
