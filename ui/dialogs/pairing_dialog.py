# -*- coding: utf-8 -*-
"""手机扫码连接弹窗：显示二维码，mDNS 发现后自动 adb pair，再发现连接服务后 adb connect。"""

import random
import string
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from adb_helper import adb_pair, adb_connect, qr_string_for_phone_scan
from core.workers import (
    Worker,
    PairingNotifier,
    ZeroconfThread,
    ConnectNotifier,
    ZeroconfConnectThread,
)
from core.utils import make_qr_pixmap, is_success_connect_output
from ui.widgets import FramelessDialog


class PairingDialog(FramelessDialog):
    """显示供手机扫描的二维码，监听 mDNS，手机扫码后自动执行 adb pair，再发现 _adb-tls-connect 后执行 adb connect。"""
    pairing_success = pyqtSignal()
    log_step = pyqtSignal(str)
    command_output = pyqtSignal(int, str, str)

    def __init__(self, parent: QMainWindow):
        super().__init__(parent, "手机扫码连接", min_width=340, min_height=420)
        self._main_parent = parent
        self._notifier = PairingNotifier(self)
        self._zeroconf_thread: ZeroconfThread | None = None
        self._pair_worker: Worker | None = None
        self._paired = False
        self._pair_host: str | None = None  # 配对时的设备 IP，用于匹配连接服务
        self._connect_notifier = ConnectNotifier(self)
        self._zeroconf_connect_thread: ZeroconfConnectThread | None = None
        self._connect_worker: Worker | None = None
        self._connect_finish_called = False
        self._connect_timeout_timer: QTimer | None = None
        self._password = "".join(random.choices(string.digits, k=6))
        self._name = "adb"
        self._setup_content()
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

    def _setup_content(self):
        layout = self.content_layout()
        layout.setSpacing(16)
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
        close_btn.setMinimumWidth(88)
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
        self._pair_host = host
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
            self._emit_step("配对成功，正在监听连接服务 _adb-tls-connect…")
            self._status.setText("配对成功，正在查找连接端口…")
            self._connect_finish_called = False
            self._connect_notifier.connect_found.connect(self._on_connect_found)
            self._zeroconf_connect_thread = ZeroconfConnectThread(self._connect_notifier)
            self._zeroconf_connect_thread.start()
            self._connect_timeout_timer = QTimer(self)
            self._connect_timeout_timer.setSingleShot(True)
            self._connect_timeout_timer.timeout.connect(self._on_connect_timeout)
            self._connect_timeout_timer.start(15000)
        else:
            self._paired = False
            self._emit_step("配对失败，请重试或关闭后再次打开")
            self._status.setText("配对失败，请重试或关闭后再次打开")

    def _on_connect_found(self, host: str, port: int):
        if self._connect_finish_called or self._pair_host is None or host != self._pair_host:
            return
        self._connect_finish_called = True
        self._stop_connect_listener()
        self._emit_step(f"发现连接服务 {host}:{port}，正在执行 adb connect…")
        self._status.setText("正在连接…")
        self._connect_worker = Worker(adb_connect, host, port)
        self._connect_worker.finished.connect(self._on_connect_finished)
        self._connect_worker.start()

    def _on_connect_finished(self, code: int, out: str, err: str):
        if self._connect_worker:
            try:
                self._connect_worker.finished.disconnect(self._on_connect_finished)
            except Exception:
                pass
            self._connect_worker = None
        try:
            self.command_output.emit(code, out, err)
        except Exception:
            pass
        if code == 0 and is_success_connect_output(out):
            self._emit_step("连接成功，设备已加入列表")
            self._status.setText("连接成功")
            self._finish_pairing()
        else:
            self._connect_finish_called = False
            self._emit_step("连接失败，请用手动连接填写连接端口重试")
            self._status.setText("连接失败，请用手动连接重试")

    def _on_connect_timeout(self):
        if self._connect_finish_called:
            return
        self._connect_finish_called = True
        self._stop_connect_listener()
        self._emit_step("未发现连接服务，配对已保存；若设备未出现请用手动连接填写连接端口")
        self._status.setText("配对成功，请用手动连接填写连接端口")
        self._finish_pairing()

    def _stop_connect_listener(self):
        if self._connect_timeout_timer:
            try:
                self._connect_timeout_timer.stop()
            except Exception:
                pass
            self._connect_timeout_timer = None
        try:
            self._connect_notifier.connect_found.disconnect(self._on_connect_found)
        except Exception:
            pass
        if self._zeroconf_connect_thread and self._zeroconf_connect_thread.isRunning():
            self._zeroconf_connect_thread.stop()
            self._zeroconf_connect_thread.wait(1000)
        self._zeroconf_connect_thread = None

    def _finish_pairing(self):
        self._stop_connect_listener()
        self._emit_step("配对与连接流程完成")
        self._status.setText("连接成功")
        self.pairing_success.emit()
        self.accept()

    def accept(self):
        self._emit_step("停止 mDNS 监听")
        self._stop_connect_listener()
        if self._zeroconf_thread and self._zeroconf_thread.isRunning():
            self._zeroconf_thread.stop()
            self._zeroconf_thread.wait(1000)
        super().accept()
