# -*- coding: utf-8 -*-
"""手动输入 IP 连接弹窗：配对+连接 或 仅连接。"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QTabWidget,
    QFormLayout,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator

from ui.widgets import FramelessDialog, CustomMessageBox


class ManualConnectDialog(FramelessDialog):
    """手动输入 IP 连接：支持配对+连接 或 仅连接。"""
    connect_requested = pyqtSignal(str, dict)  # mode, payload

    def __init__(self, parent: QMainWindow):
        super().__init__(parent, "手动连接", min_width=440, min_height=320)
        self._tabs = None
        self._setup_content()

    def _setup_content(self):
        layout = self.content_layout()
        layout.setSpacing(16)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Tab A: 配对 + 连接
        tab_pair = QWidget()
        form_pair = QFormLayout(tab_pair)
        form_pair.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_pair.setFormAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_pair.setVerticalSpacing(12)
        form_pair.setHorizontalSpacing(16)

        self.pair_ip = QLineEdit()
        self.pair_ip.setPlaceholderText("例如 192.168.1.10")
        self.pair_ip.setFixedHeight(40)
        self.pair_port = QLineEdit()
        self.pair_port.setText("37099")
        self.pair_port.setValidator(QIntValidator(1, 65535, self))
        self.pair_port.setFixedHeight(40)
        self.pair_code = QLineEdit()
        self.pair_code.setPlaceholderText("6 位配对码")
        self.pair_code.setMaxLength(6)
        self.pair_code.setValidator(QIntValidator(0, 999999, self))
        self.pair_code.setFixedHeight(40)
        self.conn_ip = QLineEdit()
        self.conn_ip.setPlaceholderText("默认同上，也可不同")
        self.conn_ip.setFixedHeight(40)
        self.conn_port = QLineEdit()
        self.conn_port.setText("5555")
        self.conn_port.setValidator(QIntValidator(1, 65535, self))
        self.conn_port.setFixedHeight(40)

        form_pair.addRow("配对 IP：", self.pair_ip)
        form_pair.addRow("配对端口：", self.pair_port)
        form_pair.addRow("配对码：", self.pair_code)
        form_pair.addRow("连接 IP：", self.conn_ip)
        form_pair.addRow("连接端口：", self.conn_port)

        self._tabs.addTab(tab_pair, "配对+连接")

        # Tab B: 仅连接
        tab_conn = QWidget()
        form_conn = QFormLayout(tab_conn)
        form_conn.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_conn.setFormAlignment(Qt.AlignmentFlag.AlignVCenter)
        form_conn.setVerticalSpacing(12)
        form_conn.setHorizontalSpacing(16)

        self.only_ip = QLineEdit()
        self.only_ip.setPlaceholderText("例如 192.168.1.10")
        self.only_ip.setFixedHeight(40)
        self.only_port = QLineEdit()
        self.only_port.setText("5555")
        self.only_port.setValidator(QIntValidator(1, 65535, self))
        self.only_port.setFixedHeight(40)
        form_conn.addRow("IP：", self.only_ip)
        form_conn.addRow("端口：", self.only_port)

        self._tabs.addTab(tab_conn, "仅连接")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumWidth(88)
        self.btn_ok = QPushButton("连接")
        self.btn_ok.setObjectName("btnPrimary")
        self.btn_ok.setMinimumWidth(88)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(lambda: self._submit(self._tabs.currentIndex()))
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        layout.addLayout(btn_row)

    def _submit(self, tab_index: int):
        if tab_index == 0:
            pair_host = self.pair_ip.text().strip()
            pair_port = int(self.pair_port.text() or "0")
            code = self.pair_code.text().strip()
            conn_host = (self.conn_ip.text().strip() or pair_host).strip()
            conn_port = int(self.conn_port.text() or "0")
            if not pair_host or not conn_host or pair_port <= 0 or conn_port <= 0 or len(code) != 6:
                CustomMessageBox.warning(self, "提示", "请填写配对 IP/端口、6 位配对码，以及连接端口。")
                return
            self.connect_requested.emit(
                "pair_then_connect",
                {
                    "pair_host": pair_host,
                    "pair_port": pair_port,
                    "code": code,
                    "connect_host": conn_host,
                    "connect_port": conn_port,
                },
            )
            self.accept()
            return

        host = self.only_ip.text().strip()
        port = int(self.only_port.text() or "0")
        if not host or port <= 0:
            CustomMessageBox.warning(self, "提示", "请填写 IP 和端口。")
            return
        self.connect_requested.emit("connect_only", {"host": host, "port": port})
        self.accept()
