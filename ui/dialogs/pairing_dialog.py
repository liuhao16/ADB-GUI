# -*- coding: utf-8 -*-
"""手机扫码连接弹窗：显示二维码，mDNS 发现后自动 adb pair。"""

import random
import string
from PyQt6.QtWidgets import QMainWindow, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from adb_helper import adb_pair, qr_string_for_phone_scan
from core.workers import Worker, PairingNotifier, ZeroconfThread
from core.utils import make_qr_pixmap
from ui.widgets import FramelessDialog


class PairingDialog(FramelessDialog):
    """显示供手机扫描的二维码，监听 mDNS，手机扫码后自动执行 adb pair。"""
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
