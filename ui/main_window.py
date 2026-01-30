# -*- coding: utf-8 -*-
"""主窗口：组合 panels、连接信号、调用 adb_helper / core。"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer

from adb_helper import (
    get_devices,
    install_apk,
    screenshot,
    shell,
    logcat,
    reboot,
    push,
    pull,
)
from core.workers import Worker
from core.utils import (
    pair_then_connect,
    connect_only,
    is_success_connect_output,
    is_success_pair_output,
)
from ui.widgets import CustomMessageBox, CustomInputDialog
from ui.panels import DeviceBarPanel, QuickActionsPanel, ShellPanel, OutputPanel
from ui.dialogs import PairingDialog, ManualConnectDialog, DevicePathDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADB 快捷操作")
        self.setMinimumSize(720, 560)
        self.resize(880, 640)
        self._worker = None
        self._auto_prompted_connect = False
        self._setup_ui()
        self._connect_signals()
        self._refresh_devices(allow_auto_prompt=True)

    def _setup_ui(self):
        container = QWidget()
        container.setObjectName("container")
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        self._device_bar = DeviceBarPanel()
        layout.addWidget(self._device_bar)

        self._quick_actions = QuickActionsPanel()
        layout.addWidget(self._quick_actions)

        self._shell_panel = ShellPanel()
        layout.addWidget(self._shell_panel)

        self._output_panel = OutputPanel()
        layout.addWidget(self._output_panel)

        main_layout.addWidget(central)

    def _connect_signals(self):
        self._device_bar.device_changed.connect(self._on_device_changed)
        self._device_bar.refresh_clicked.connect(self._refresh_devices)
        self._device_bar.scan_connect_clicked.connect(self._on_scan_connect)
        self._device_bar.manual_connect_clicked.connect(self._on_manual_connect)

        self._quick_actions.install_apk_clicked.connect(self._on_install_apk)
        self._quick_actions.screenshot_clicked.connect(self._on_screenshot)
        self._quick_actions.logcat_clicked.connect(self._on_logcat)
        self._quick_actions.reboot_clicked.connect(self._on_reboot)
        self._quick_actions.push_clicked.connect(self._on_push)
        self._quick_actions.pull_clicked.connect(self._on_pull)
        self._quick_actions.shell_dialog_clicked.connect(self._on_shell_dialog)

        self._shell_panel.shell_requested.connect(self._on_shell_requested)

    def _on_device_changed(self, index: int):
        pass  # 当前设备由 current_serial() 实时获取

    def _device(self) -> str:
        return self._device_bar.current_serial()

    def _log_step(self, msg: str):
        self._output_panel.append_step(msg)

    def _set_status(self, msg: str):
        self._output_panel.set_status(msg)

    def _refresh_devices(self, *, allow_auto_prompt: bool = False):
        self._log_step("正在刷新设备列表…")
        self._device_bar.clear_devices()
        devices = get_devices()
        for d in devices:
            label = f"{d['serial']} ({d['model']})" if d.get("model") else d["serial"]
            self._device_bar.add_device(label, d["serial"])
        if devices:
            self._device_bar.set_current_index(0)
            self._log_step(f"已检测到 {len(devices)} 台设备")
            self._set_status(f"已连接 {len(devices)} 台设备")
        else:
            self._log_step("未检测到设备")
            self._set_status("未检测到设备，请连接并开启 USB 调试")
            if allow_auto_prompt and not self._auto_prompted_connect:
                self._auto_prompted_connect = True
                QTimer.singleShot(150, self._on_scan_connect)

    def _ensure_device(self) -> bool:
        if not self._device():
            CustomMessageBox.warning(self, "提示", "请先选择设备")
            return False
        return True

    def _on_scan_connect(self):
        self._log_step("打开扫码连接窗口")
        dlg = PairingDialog(self)
        dlg.log_step.connect(self._log_step)
        dlg.command_output.connect(self._output_panel.append_output)
        dlg.pairing_success.connect(self._refresh_devices)
        dlg.pairing_success.connect(lambda: self._set_status("无线连接成功，已刷新设备列表"))
        dlg.exec()
        self._log_step("扫码连接窗口已关闭")

    def _on_manual_connect(self):
        self._log_step("打开手动连接窗口")
        dlg = ManualConnectDialog(self)
        dlg.connect_requested.connect(self._on_manual_connect_requested)
        dlg.exec()
        self._log_step("手动连接窗口已关闭")

    def _on_manual_connect_requested(self, mode: str, payload: dict):
        if mode == "pair_then_connect":
            self._log_step(
                f"手动连接：配对 {payload['pair_host']}:{payload['pair_port']}，再连接 {payload['connect_host']}:{payload['connect_port']}"
            )
            self._run_worker(
                pair_then_connect,
                payload["pair_host"],
                payload["pair_port"],
                payload["code"],
                payload["connect_host"],
                payload["connect_port"],
            )
            return
        if mode == "connect_only":
            self._log_step(f"手动连接：连接 {payload['host']}:{payload['port']}")
            self._run_worker(connect_only, payload["host"], payload["port"])

    def _run_worker(self, func, *args, **kwargs):
        if self._worker and self._worker.isRunning():
            self._log_step("请等待当前命令执行完成")
            self._set_status("请等待当前命令执行完成")
            return
        self._worker = Worker(func, *args, **kwargs)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        self._log_step("命令执行中…")
        self._set_status("执行中...")
        self._device_bar.set_refresh_enabled(False)

    def _on_worker_finished(self, code: int, out: str, err: str):
        self._device_bar.set_refresh_enabled(True)
        self._log_step("命令执行完成")
        self._output_panel.append_output(code, out, err)
        out_text = out or ""
        if code == 0 and (
            is_success_connect_output(out_text)
            or is_success_pair_output(out_text)
            or "adb pair" in out_text.lower()
            or "adb connect" in out_text.lower()
        ):
            self._refresh_devices()
            self._set_status("连接成功，已刷新设备列表")
        else:
            self._set_status("命令执行完成")

    def _on_install_apk(self):
        if not self._ensure_device():
            return
        self._log_step("选择 APK 文件…")
        path, _ = QFileDialog.getOpenFileName(self, "选择 APK", "", "APK (*.apk);;所有文件 (*)")
        if not path:
            self._log_step("已取消选择")
            return
        self._log_step(f"安装 APK: {path}")
        self._run_worker(install_apk, self._device(), path)

    def _on_screenshot(self):
        if not self._ensure_device():
            return
        self._log_step("选择截图保存路径…")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存截图", f"screenshot_{self._device()[:8]}.png", "PNG (*.png);;所有文件 (*)"
        )
        if not path:
            self._log_step("已取消保存")
            return
        self._log_step(f"截图并保存到: {path}")
        self._run_worker(screenshot, self._device(), path)

    def _on_logcat(self):
        if not self._ensure_device():
            return
        self._log_step("获取 Logcat（最近 500 行）…")
        self._run_worker(logcat, self._device(), clear=False, max_lines=500)

    def _on_reboot(self):
        if not self._ensure_device():
            return
        reply = CustomMessageBox.question(self, "确认", "是否重启设备？")
        if reply != CustomMessageBox.YES:
            self._log_step("已取消重启")
            return
        self._log_step("正在重启设备…")
        self._run_worker(reboot, self._device())

    def _on_push(self):
        if not self._ensure_device():
            return
        self._log_step("选择要推送的本地文件…")
        local, _ = QFileDialog.getOpenFileName(self, "选择本地文件", "", "所有文件 (*)")
        if not local:
            self._log_step("已取消推送")
            return
        self._log_step("选择设备上的目标路径（文件夹）…")
        dlg = DevicePathDialog(self, self._device(), initial_path="/storage/emulated/0", mode="push")
        dlg.exec()
        remote_dir = dlg.selected_path()
        if not remote_dir:
            self._log_step("已取消推送")
            return
        remote = f"{remote_dir.rstrip('/')}/{Path(local).name}"
        self._log_step(f"推送文件: {local} -> {remote}")
        self._run_worker(push, self._device(), local, remote)

    def _on_pull(self):
        if not self._ensure_device():
            return
        self._log_step("选择设备上的文件或文件夹…")
        dlg = DevicePathDialog(self, self._device(), initial_path="/storage/emulated/0", mode="pull")
        dlg.exec()
        remote = dlg.selected_path()
        if not remote:
            self._log_step("已取消拉取")
            return
        default_name = Path(remote).name or "device_file"
        self._log_step("选择保存到本地的位置…")
        if dlg.selected_is_dir():
            local = QFileDialog.getExistingDirectory(self, "选择保存到的文件夹", default_name)
        else:
            local, _ = QFileDialog.getSaveFileName(self, "保存到", default_name, "所有文件 (*)")
        if not local:
            self._log_step("已取消保存")
            return
        self._log_step(f"拉取文件: {remote} -> {local}")
        self._run_worker(pull, self._device(), remote, local)

    def _on_shell_dialog(self):
        if not self._ensure_device():
            return
        self._log_step("输入自定义 Shell 命令…")
        cmd, ok = CustomInputDialog.getText(self, "Shell 命令", "输入 shell 命令:")
        if ok and cmd.strip():
            self._run_shell(cmd.strip())
        else:
            self._log_step("已取消")

    def _on_shell_requested(self, cmd: str):
        if not cmd:
            self._log_step("Shell 命令为空，未执行")
            return
        if not self._ensure_device():
            return
        self._run_shell(cmd)

    def _run_shell(self, cmd: str):
        self._log_step(f"执行 Shell: {cmd}")
        self._run_worker(shell, self._device(), cmd)
