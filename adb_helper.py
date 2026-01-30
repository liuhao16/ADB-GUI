# -*- coding: utf-8 -*-
"""ADB 命令封装，通过 subprocess 调用系统 adb。"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

# 项目内 platform-tools 目录（与 adb_helper.py 同级的 platform-tools）
_PLATFORM_TOOLS_DIR = Path(__file__).resolve().parent / "platform-tools"
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
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
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
