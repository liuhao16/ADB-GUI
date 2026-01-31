# -*- coding: utf-8 -*-
"""ADB 命令封装，通过 subprocess 调用系统 adb。"""

import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional


def _get_base_dir() -> Path:
    """开发时用脚本所在目录，打包成 exe 后用 PyInstaller 解压目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


# 项目内 platform-tools 目录（开发时与 adb_helper.py 同级，打包后在 exe 同目录）
_PLATFORM_TOOLS_DIR = _get_base_dir() / "platform-tools"
_ADB_NAME = "adb.exe" if os.name == "nt" else "adb"


def _find_adb() -> Optional[str]:
    """优先使用项目内 platform-tools 下的 adb，否则查找系统 PATH。"""
    local_adb = _PLATFORM_TOOLS_DIR / _ADB_NAME
    if local_adb.is_file():
        return str(local_adb)
    return shutil.which("adb")


def run_adb(*args: str, device: Optional[str] = None, timeout: int = 30) -> tuple[int, str, str]:
    """
    执行 adb 命令。
    :param args: adb 子命令及参数，如 ("devices", "-l")
    :param device: 设备序列号，None 表示不指定设备
    :param timeout: 超时秒数
    :return: (returncode, stdout, stderr)
    """
    adb_path = _find_adb()
    if not adb_path:
        return -1, "", "未找到 adb，请将 Android SDK platform-tools 置于项目 platform-tools 目录或加入系统 PATH"
    cmd = [adb_path]
    if device:
        cmd.extend(["-s", device])
    cmd.extend(args)
    # Windows 下禁止 adb 子进程弹出控制台，避免黑框一闪而过
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def get_devices() -> list[dict]:
    """
    获取已连接设备列表。
    :return: [{"serial": "xxx", "status": "device", "model": "..."}, ...]
    """
    code, out, err = run_adb("devices", "-l")
    if code != 0:
        return []
    devices = []
    for line in out.strip().splitlines()[1:]:  # 跳过 "List of devices attached"
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, status = parts[0], parts[1]
        model = ""
        for p in parts[2:]:
            if p.startswith("model:"):
                model = p.replace("model:", "").strip()
                break
        devices.append({"serial": serial, "status": status, "model": model})
    return [d for d in devices if d["status"] == "device"]


def install_apk(device: str, apk_path: str, replace: bool = True) -> tuple[int, str, str]:
    """安装 APK。replace=True 时覆盖安装。"""
    args = ["install", "-r" if replace else "", apk_path]
    args = [x for x in args if x]
    return run_adb(*args, device=device, timeout=120)


def uninstall_app(device: str, package: str) -> tuple[int, str, str]:
    """卸载应用。"""
    return run_adb("uninstall", package, device=device)


def screenshot(device: str, save_path: str) -> tuple[int, str, str]:
    """截图并拉取到本地。"""
    remote = "/sdcard/adb_screenshot.png"
    code, out, err = run_adb("shell", "screencap", "-p", remote, device=device)
    if code != 0:
        return code, out, err
    return run_adb("pull", remote, save_path, device=device)


def start_screen_record(device: str, save_path: str, duration: int = 180) -> tuple[int, str, str]:
    """开始录屏（在设备上录制，结束后需 pull）。duration 秒。"""
    remote = "/sdcard/adb_record.mp4"
    code, out, err = run_adb(
        "shell", "screenrecord", "--time-limit", str(duration), remote,
        device=device, timeout=duration + 30
    )
    if code != 0:
        return code, out, err
    return run_adb("pull", remote, save_path, device=device, timeout=60)


def shell(device: str, command: str, timeout: int = 30) -> tuple[int, str, str]:
    """执行 shell 命令。"""
    return run_adb("shell", command, device=device, timeout=timeout)


def push(device: str, local: str, remote: str, timeout: int = 60) -> tuple[int, str, str]:
    """推送本地文件到设备。"""
    return run_adb("push", local, remote, device=device, timeout=timeout)


def pull(device: str, remote: str, local: str, timeout: int = 60) -> tuple[int, str, str]:
    """从设备拉取文件到本地。"""
    return run_adb("pull", remote, local, device=device, timeout=timeout)


def list_device_path(device: str, path: str) -> tuple[list[dict], Optional[str]]:
    """
    列出设备上指定路径下的目录和文件。
    兼容不同 Android 的 ls -la 输出（列数可能为 7/8/9 等），并正确处理符号链接名称。
    :param device: 设备序列号
    :param path: 设备上的绝对路径，如 /sdcard 或 /storage/emulated/0
    :return: (entries, error)。entries 为 [{"name": str, "is_dir": bool, "target": str|None}, ...]；error 非空表示失败原因。
    """
    path = path.strip().rstrip("/") or "/"
    code, out, err = run_adb("shell", "ls", "-la", path, device=device, timeout=15)
    if code != 0:
        return [], err.strip() or out.strip() or "无法访问该路径"
    entries = []
    lines = out.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("total "):
            continue
        # 兼容不同列数：标准为 perm nlink user group size month day time name；部分设备无 group 则 8 列。
        parts = line.split()
        if len(parts) < 8:
            if len(parts) >= 2 and parts[-1] in (".", ".."):
                if parts[-1] == "..":
                    entries.append({"name": "..", "is_dir": True, "target": None})
                continue
            continue
        perm = parts[0]
        if perm[0] not in ("d", "l", "-"):
            continue
        if len(parts) >= 9:
            raw_name = " ".join(parts[8:]).strip()
        else:
            raw_name = parts[7] if len(parts) >= 8 else ""
        if " -> " in raw_name:
            name, target = raw_name.split(" -> ", 1)
            name = name.strip()
            target = target.strip()
        else:
            name = raw_name
            target = None
        if name in (".", ".."):
            if name == "..":
                entries.append({"name": "..", "is_dir": True, "target": None})
            continue
        # d=目录，l=符号链接（有 target 时点击进入目标路径）
        is_dir = perm.startswith("d") or perm.startswith("l")
        entries.append({"name": name, "is_dir": is_dir, "target": target})
    if path != "/" and not any(e["name"] == ".." for e in entries):
        entries.insert(0, {"name": "..", "is_dir": True, "target": None})
    return entries, None


def get_installed_packages(device: str, include_system: bool = False) -> tuple[int, list[str], str]:
    """获取已安装的应用包名列表。include_system=False 时仅返回第三方应用(-3)。"""
    # -3: show only third party packages
    flags = [] if include_system else ["-3"]
    code, out, err = run_adb("shell", "pm", "list", "packages", *flags, device=device)
    if code != 0:
        return code, [], err
    
    packages = []
    for line in out.strip().splitlines():
        # output format: "package:com.example.app"
        line = line.strip()
        if line.startswith("package:"):
            packages.append(line.replace("package:", ""))
    return 0, "\n".join(sorted(packages)), ""


def get_package_path(device: str, package: str) -> tuple[int, str, str]:
    """获取应用的 APK 路径。"""
    # output format: "package:/data/app/~~.../base.apk"
    code, out, err = run_adb("shell", "pm", "path", package, device=device)
    if code != 0:
        return code, "", err
    
    #可能有多个路径（split apk），通常取第一个 base.apk
    for line in out.strip().splitlines():
        if line.startswith("package:"):
            return 0, line.replace("package:", "").strip(), ""
            
    return -1, "", "未找到 APK 路径"


def logcat(device: str, clear: bool = False, max_lines: Optional[int] = None) -> tuple[int, str, str]:
    """获取 logcat。clear 先清空；max_lines 限制行数。"""
    if clear:
        run_adb("logcat", "-c", device=device)
    args = ["logcat", "-d"]
    if max_lines:
        args.extend(["-t", str(max_lines)])
    return run_adb(*args, device=device, timeout=15)


def reboot(device: str, mode: str = "") -> tuple[int, str, str]:
    """重启设备。mode: 空=普通重启, bootloader, recovery。"""
    if mode:
        return run_adb("reboot", mode, device=device)
    return run_adb("reboot", device=device)


# ---------- 无线连接（手机扫码配对） ----------


def adb_pair(host: str, port: int, code: str) -> tuple[int, str, str]:
    """Android 11+ 无线配对：adb pair host:port 六位配对码。"""
    return run_adb("pair", f"{host}:{port}", code, timeout=30)


def adb_connect(host: str, port: int) -> tuple[int, str, str]:
    """无线连接：adb connect host:port。"""
    return run_adb("connect", f"{host}:{port}", timeout=15)


def qr_string_for_phone_scan(name: str, password: str) -> str:
    """
    生成供手机扫描的二维码内容（Android 11+ 无线调试「使用二维码配对设备」）。
    手机扫描后会在本机通过 mDNS 暴露配对服务，PC 再执行 adb pair。
    格式：WIFI:T:ADB;S:<name>;P:<password>;;
    """
    return f"WIFI:T:ADB;S:{name};P:{password};;"
