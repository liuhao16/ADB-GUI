# -*- coding: utf-8 -*-
"""ADB 快捷操作 - PyQt6 图形界面。"""

import random
import socket
import string
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QGroupBox,
    QGridLayout,
    QInputDialog,
    QDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPixmap, QImage

from adb_helper import (
    get_devices,
    run_adb,
    install_apk,
    screenshot,
    shell,
    logcat,
    reboot,
    push,
    pull,
    adb_pair,
    qr_string_for_phone_scan,
)


class Worker(QThread):
    """在后台执行可调用对象，避免阻塞 UI。"""
    finished = pyqtSignal(int, str, str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            if isinstance(result, tuple) and len(result) == 3:
                self.finished.emit(*result)
            else:
                self.finished.emit(0, str(result), "")
        except Exception as e:
            self.finished.emit(-1, "", str(e))


class PairingNotifier(QObject):
    """供 zeroconf 回调跨线程通知主线程：发现配对服务。"""
    pair_found = pyqtSignal(str, int, str)  # host, port, password


class PairingListener:
    """mDNS 监听 _adb-tls-pairing，发现后通过 notifier 发出 host/port/密码。"""
    def __init__(self, notifier: PairingNotifier, password: str):
        self.notifier = notifier
        self.password = password

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if not info or not info.addresses:
            return
        host = socket.inet_ntoa(info.addresses[0])
        port = info.port
        self.notifier.pair_found.emit(host, port, self.password)

    def remove_service(self, zeroconf, service_type, name):
        pass

    def update_service(self, zeroconf, service_type, name):
        pass


class ZeroconfThread(QThread):
    """在后台运行 zeroconf 监听配对服务，发现后由 notifier 发信号。"""
    def __init__(self, notifier: PairingNotifier, password: str):
        super().__init__()
        self.notifier = notifier
        self.password = password
        self._running = True
        self._zc = None

    def run(self):
        try:
            from zeroconf import Zeroconf, ServiceBrowser
            self._zc = Zeroconf()
            listener = PairingListener(self.notifier, self.password)
            ServiceBrowser(
                self._zc,
                "_adb-tls-pairing._tcp.local.",
                listener,
            )
            while self._running:
                self.msleep(300)
        except Exception:
            pass
        finally:
            if self._zc is not None:
                try:
                    self._zc.close()
                except Exception:
                    pass
                self._zc = None

    def stop(self):
        self._running = False


def make_qr_pixmap(text: str, box_size: int = 8) -> QPixmap:
    """根据字符串生成二维码 QPixmap。"""
    import qrcode
    qr = qrcode.QRCode(box_size=box_size, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")
    w, h = img.size
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


class PairingDialog(QDialog):
    """显示供手机扫描的二维码，监听 mDNS，手机扫码后自动执行 adb pair。"""
    pairing_success = pyqtSignal()
    log_step = pyqtSignal(str)  # 步骤说明，由主窗口输出到输出区
    command_output = pyqtSignal(int, str, str)  # 配对/连接命令的 code, out, err，由主窗口追加到输出区

    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.setWindowTitle("手机扫码连接")
        self.setMinimumSize(320, 380)
        self._parent = parent
        self._notifier = PairingNotifier(self)
        self._zeroconf_thread: ZeroconfThread | None = None
        self._pair_worker: Worker | None = None
        self._paired = False
        # 随机六位数字作为配对码
        self._password = "".join(random.choices(string.digits, k=6))
        self._name = "adb"
        self._setup_ui()
        self._start_listener()

    def _emit_step(self, msg: str):
        try:
            self.log_step.emit(msg)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._emit_step("生成二维码，等待手机扫描…")
        self._emit_step("已启动 mDNS 监听 _adb-tls-pairing")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        qr_text = qr_string_for_phone_scan(self._name, self._password)
        pixmap = make_qr_pixmap(qr_text)
        label_qr = QLabel()
        label_qr.setPixmap(pixmap)
        label_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_qr)
        hint = QLabel(
            "请使用手机打开：\n"
            "开发者选项 → 无线调试 → 使用二维码配对设备\n"
            "然后扫描上方二维码完成配对。"
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self._status = QLabel("等待手机扫描…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self._notifier.pair_found.connect(self._on_pair_found)

    def _start_listener(self):
        self._zeroconf_thread = ZeroconfThread(self._notifier, self._password)
        self._zeroconf_thread.start()

    def _on_pair_found(self, host: str, port: int, password: str):
        if self._paired:
            return
        self._paired = True
        self._emit_step(f"发现设备 {host}:{port}，正在执行 adb pair…")
        self._status.setText(f"发现设备 {host}:{port}，正在配对…")
        self._pair_worker = Worker(adb_pair, host, port, password)
        self._pair_worker.finished.connect(self._on_pair_finished)
        self._pair_worker.start()

    def _on_pair_finished(self, code: int, out: str, err: str):
        if self._pair_worker:
            try:
                self._pair_worker.finished.disconnect(self._on_pair_finished)
            except Exception:
                pass
            self._pair_worker = None
        try:
            self.command_output.emit(code, out, err)
        except Exception:
            pass
        if code == 0 and "Successfully paired" in out:
            self._emit_step("配对成功，ADB 将自动完成连接，稍后刷新设备列表…")
            self._status.setText("配对成功")
            # 配对成功后 ADB 会自动通过 mDNS 连接，等待 2 秒让其完成
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self._finish_pairing)
        else:
            self._paired = False
            self._emit_step("配对失败，请重试或关闭后再次打开")
            self._status.setText("配对失败，请重试或关闭后再次打开")

    def _finish_pairing(self):
        self._emit_step("配对流程完成，设备已加入列表")
        self._status.setText("连接成功")
        self.pairing_success.emit()
        self.accept()

    def accept(self):
        self._emit_step("停止 mDNS 监听")
        if self._zeroconf_thread and self._zeroconf_thread.isRunning():
            self._zeroconf_thread.stop()
            self._zeroconf_thread.wait(1000)
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADB 快捷操作")
        self.setMinimumSize(720, 560)
        self.resize(880, 640)
        self._worker = None
        self._device = ""
        self._setup_ui()
        self._refresh_devices()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 设备选择
        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(320)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        dev_layout.addWidget(self.device_combo)
        self.btn_refresh = QPushButton("刷新设备")
        self.btn_refresh.clicked.connect(self._refresh_devices)
        dev_layout.addWidget(self.btn_refresh)
        self.btn_scan_connect = QPushButton("扫码连接")
        self.btn_scan_connect.clicked.connect(self._on_scan_connect)
        dev_layout.addWidget(self.btn_scan_connect)
        dev_layout.addStretch()
        layout.addLayout(dev_layout)

        # 快捷操作区
        group = QGroupBox("快捷操作")
        group_layout = QGridLayout()
        row, col = 0, 0
        actions = [
            ("安装 APK", self._on_install_apk),
            ("截图", self._on_screenshot),
            ("Logcat", self._on_logcat),
            ("重启", self._on_reboot),
            ("推送文件", self._on_push),
            ("拉取文件", self._on_pull),
            ("自定义 Shell", self._on_shell_dialog),
        ]
        for text, slot in actions:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            group_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        group.setLayout(group_layout)
        layout.addWidget(group)

        # Shell 单行输入
        shell_layout = QHBoxLayout()
        shell_layout.addWidget(QLabel("Shell 命令:"))
        self.shell_edit = QLineEdit()
        self.shell_edit.setPlaceholderText("输入 adb shell 命令，如: pm list packages")
        self.shell_edit.returnPressed.connect(self._run_shell_quick)
        shell_layout.addWidget(self.shell_edit)
        self.btn_shell = QPushButton("执行")
        self.btn_shell.clicked.connect(self._run_shell_quick)
        shell_layout.addWidget(self.btn_shell)
        layout.addLayout(shell_layout)

        # 输出区
        out_label = QLabel("输出:")
        layout.addWidget(out_label)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setMinimumHeight(220)
        layout.addWidget(self.output)

        # 状态栏
        self.statusBar().showMessage("就绪。请连接设备并开启 USB 调试。")

    def _log_step(self, msg: str):
        """在输出区追加一步操作说明。"""
        self.output.append(f"[步骤] {msg}")
        self.output.ensureCursorVisible()

    def _on_device_changed(self, index):
        if index < 0:
            self._device = ""
            return
        self._device = self.device_combo.currentData() or ""

    def _refresh_devices(self):
        self._log_step("正在刷新设备列表…")
        self.device_combo.clear()
        devices = get_devices()
        for d in devices:
            label = f"{d['serial']} ({d['model']})" if d.get("model") else d["serial"]
            self.device_combo.addItem(label, d["serial"])
        if devices:
            self.device_combo.setCurrentIndex(0)
            self._device = devices[0]["serial"]
            self._log_step(f"已检测到 {len(devices)} 台设备")
            self.statusBar().showMessage(f"已连接 {len(devices)} 台设备")
        else:
            self._device = ""
            self._log_step("未检测到设备")
            self.statusBar().showMessage("未检测到设备，请连接并开启 USB 调试")

    def _ensure_device(self) -> bool:
        if not self._device:
            QMessageBox.warning(self, "提示", "请先选择设备")
            return False
        return True

    def _on_scan_connect(self):
        """手机扫码连接：弹出二维码窗口，手机扫描后通过 mDNS 自动配对。"""
        self._log_step("打开扫码连接窗口")
        dlg = PairingDialog(self)
        dlg.log_step.connect(self._log_step)
        dlg.command_output.connect(self._append_output)
        dlg.pairing_success.connect(self._refresh_devices)
        dlg.pairing_success.connect(lambda: self.statusBar().showMessage("无线连接成功，已刷新设备列表"))
        dlg.exec()
        self._log_step("扫码连接窗口已关闭")

    def _append_output(self, code: int, out: str, err: str):
        self.output.append("---")
        if out:
            self.output.append(out.rstrip())
        if err:
            self.output.append(f"[stderr] {err.rstrip()}")
        self.output.append(f"[退出码: {code}]")
        self.output.ensureCursorVisible()

    def _run_worker(self, func, *args, **kwargs):
        if self._worker and self._worker.isRunning():
            self._log_step("请等待当前命令执行完成")
            self.statusBar().showMessage("请等待当前命令执行完成")
            return
        self._worker = Worker(func, *args, **kwargs)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        self._log_step("命令执行中…")
        self.statusBar().showMessage("执行中...")
        self.btn_refresh.setEnabled(False)

    def _on_worker_finished(self, code: int, out: str, err: str):
        self.btn_refresh.setEnabled(True)
        self._log_step("命令执行完成")
        self._append_output(code, out, err)
        self.statusBar().showMessage("命令执行完成")

    def _on_install_apk(self):
        if not self._ensure_device():
            return
        self._log_step("选择 APK 文件…")
        path, _ = QFileDialog.getOpenFileName(self, "选择 APK", "", "APK (*.apk);;所有文件 (*)")
        if not path:
            self._log_step("已取消选择")
            return
        self._log_step(f"安装 APK: {path}")
        self._run_worker(install_apk, self._device, path)

    def _on_screenshot(self):
        if not self._ensure_device():
            return
        self._log_step("选择截图保存路径…")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存截图", f"screenshot_{self._device[:8]}.png", "PNG (*.png);;所有文件 (*)"
        )
        if not path:
            self._log_step("已取消保存")
            return
        self._log_step(f"截图并保存到: {path}")
        self._run_worker(screenshot, self._device, path)

    def _on_logcat(self):
        if not self._ensure_device():
            return
        self._log_step("获取 Logcat（最近 500 行）…")
        self._run_worker(logcat, self._device, clear=False, max_lines=500)

    def _on_reboot(self):
        if not self._ensure_device():
            return
        reply = QMessageBox.question(
            self, "确认", "是否重启设备？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._log_step("已取消重启")
            return
        self._log_step("正在重启设备…")
        self._run_worker(reboot, self._device)

    def _on_push(self):
        if not self._ensure_device():
            return
        self._log_step("选择要推送的本地文件…")
        local, _ = QFileDialog.getOpenFileName(self, "选择本地文件", "", "所有文件 (*)")
        if not local:
            self._log_step("已取消推送")
            return
        remote = f"/sdcard/{Path(local).name}"
        self._log_step(f"推送文件: {local} -> {remote}")
        self._run_worker(push, self._device, local, remote)

    def _on_pull(self):
        if not self._ensure_device():
            return
        self._log_step("输入设备路径并选择保存位置…")
        remote, ok = QInputDialog.getText(self, "拉取文件", "设备路径 (如 /sdcard/xxx):")
        if not ok or not remote.strip():
            self._log_step("已取消拉取")
            return
        local, _ = QFileDialog.getSaveFileName(self, "保存到", Path(remote).name, "所有文件 (*)")
        if not local:
            self._log_step("已取消保存")
            return
        self._log_step(f"拉取文件: {remote.strip()} -> {local}")
        self._run_worker(pull, self._device, remote.strip(), local)

    def _on_shell_dialog(self):
        if not self._ensure_device():
            return
        self._log_step("输入自定义 Shell 命令…")
        cmd, ok = QInputDialog.getText(self, "Shell 命令", "输入 shell 命令:")
        if ok and cmd.strip():
            self._run_shell(cmd.strip())
        else:
            self._log_step("已取消")

    def _run_shell_quick(self):
        cmd = self.shell_edit.text().strip()
        if not cmd:
            self._log_step("Shell 命令为空，未执行")
            return
        if not self._ensure_device():
            return
        self._run_shell(cmd)

    def _run_shell(self, cmd: str):
        self._log_step(f"执行 Shell: {cmd}")
        self._run_worker(shell, self._device, cmd)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
