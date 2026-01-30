# -*- coding: utf-8 -*-
"""主窗口内功能块：设备栏、快捷操作、Shell 单行、输出区。"""

from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QListView,
    QPushButton,
    QGroupBox,
    QGridLayout,
    QLineEdit,
    QScrollArea,
    QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from ui.theme import (
    ACCENT,
    ACCENT_FOREGROUND,
    BORDER,
    CARD,
    FOREGROUND,
    MUTED_FOREGROUND,
    PRIMARY,
    PRIMARY_FOREGROUND,
    RADIUS,
    RADIUS_SM,
)


def _combo_popup_stylesheet() -> str:
    """弹出层独立窗口用样式，与 theme 中 QComboBox 下拉一致（Windows 下 reparent 后仍生效）。"""
    return f"""
        QWidget#comboPopupContainer {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 0;
        }}
        QListView {{
            background: {CARD};
            border: none;
            border-radius: 0;
            padding: 6px;
            outline: none;
        }}
        QListView QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 4px 2px 4px 0;
            border-radius: 0;
        }}
        QListView QScrollBar::handle:vertical {{
            background: {BORDER};
            border-radius: 0;
            min-height: 32px;
        }}
        QListView QScrollBar::handle:vertical:hover {{
            background: {MUTED_FOREGROUND};
        }}
        QListView QScrollBar::add-line:vertical, QListView QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QListView QScrollBar::add-page:vertical, QListView QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QListView::item {{
            min-height: 36px;
            height: 36px;
            padding: 0 12px;
            margin: 1px 4px;
            border-radius: 0;
            color: {FOREGROUND};
        }}
        QListView::item:selected {{
            background: {PRIMARY};
            color: {PRIMARY_FOREGROUND};
        }}
        QListView::item:selected:hover {{
            background: {PRIMARY};
            color: {PRIMARY_FOREGROUND};
        }}
        QListView::item:hover:!selected {{
            background: {ACCENT};
            color: {ACCENT_FOREGROUND};
        }}
    """


class StyledComboBox(QComboBox):
    """下拉直角、统一主题样式；弹出层高度按项数计算，并隐藏顶部三角。"""
    # 与 theme 中 item 一致：高度 + 上下 margin
    _ITEM_HEIGHT = 36 + 2 * 2  # 40
    _LIST_PADDING = 12

    def showPopup(self):
        super().showPopup()
        QTimer.singleShot(0, self._adjust_popup)

    def _adjust_popup(self):
        view = self.view()
        popup = view.window() if view else None
        if not popup or popup == self:
            return
        popup.setObjectName("comboPopupContainer")
        popup.setStyleSheet(_combo_popup_stylesheet())
        # 按项数设置最小高度，保证至少显示 2 项或全部（不超过 maxVisibleItems）
        n = self.count()
        if n > 0:
            visible = min(n, self.maxVisibleItems())
            min_h = visible * self._ITEM_HEIGHT + self._LIST_PADDING
            view.setMinimumHeight(min_h)
        # 隐藏弹出层顶部用于绘制“三角”的直接子控件（只隐藏非 QScrollArea 的）
        for child in popup.findChildren(QWidget):
            if child.parentWidget() != popup:
                continue
            if isinstance(child, QScrollArea):
                continue
            child.setMaximumHeight(0)
            child.setVisible(False)


class DeviceBarPanel(QWidget):
    """设备选择与连接按钮栏。"""
    refresh_clicked = pyqtSignal()
    scan_connect_clicked = pyqtSignal()
    manual_connect_clicked = pyqtSignal()
    device_changed = pyqtSignal(int)  # currentIndexChanged

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("deviceBar")
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("设备")
        lbl.setMinimumWidth(36)
        layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        self.device_combo = StyledComboBox()
        self.device_combo.setMinimumWidth(280)
        self.device_combo.setFixedHeight(40)
        self.device_combo.setView(QListView(self.device_combo))
        self.device_combo.setMaxVisibleItems(8)
        self.device_combo.currentIndexChanged.connect(self.device_changed.emit)
        layout.addWidget(self.device_combo, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_refresh = QPushButton("刷新设备")
        self.btn_refresh.setObjectName("btnPrimary")
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.btn_refresh, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_scan_connect = QPushButton("扫码连接")
        self.btn_scan_connect.setObjectName("btnPrimary")
        self.btn_scan_connect.clicked.connect(self.scan_connect_clicked.emit)
        layout.addWidget(self.btn_scan_connect, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_manual_connect = QPushButton("手动连接")
        self.btn_manual_connect.clicked.connect(self.manual_connect_clicked.emit)
        layout.addWidget(self.btn_manual_connect, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()

    def clear_devices(self):
        self.device_combo.clear()

    def add_device(self, label: str, serial: str):
        self.device_combo.addItem(label, serial)

    def set_current_index(self, index: int):
        self.device_combo.setCurrentIndex(index)

    def current_serial(self) -> str:
        return self.device_combo.currentData() or ""

    def set_refresh_enabled(self, enabled: bool):
        self.btn_refresh.setEnabled(enabled)


class QuickActionsPanel(QWidget):
    """快捷操作按钮网格。"""
    install_apk_clicked = pyqtSignal()
    screenshot_clicked = pyqtSignal()
    logcat_clicked = pyqtSignal()
    reboot_clicked = pyqtSignal()
    push_clicked = pyqtSignal()
    pull_clicked = pyqtSignal()
    shell_dialog_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("quickActionsPanel")
        group = QGroupBox("快捷操作")
        group_layout = QGridLayout()
        group_layout.setHorizontalSpacing(12)
        group_layout.setVerticalSpacing(12)

        actions = [
            ("安装 APK", self.install_apk_clicked),
            ("截图", self.screenshot_clicked),
            ("Logcat", self.logcat_clicked),
            ("重启", self.reboot_clicked),
            ("推送文件", self.push_clicked),
            ("拉取文件", self.pull_clicked),
            ("自定义 Shell", self.shell_dialog_clicked),
        ]
        row, col = 0, 0
        for text, sig in actions:
            btn = QPushButton(text)
            btn.clicked.connect(sig.emit)
            group_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        group.setLayout(group_layout)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)


class ShellPanel(QWidget):
    """Shell 单行输入与执行按钮。"""
    shell_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellPanel")
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel("Shell")
        lbl.setMinimumWidth(36)
        layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        self.shell_edit = QLineEdit()
        self.shell_edit.setPlaceholderText("输入 adb shell 命令，如 pm list packages")
        self.shell_edit.setFixedHeight(40)
        self.shell_edit.returnPressed.connect(self._on_execute)
        layout.addWidget(self.shell_edit, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_shell = QPushButton("执行")
        self.btn_shell.setObjectName("btnPrimary")
        self.btn_shell.clicked.connect(self._on_execute)
        layout.addWidget(self.btn_shell, 0, Qt.AlignmentFlag.AlignVCenter)

    def _on_execute(self):
        cmd = self.shell_edit.text().strip()
        if cmd:
            self.shell_requested.emit(cmd)

    def shell_text(self) -> str:
        return self.shell_edit.text().strip()


class OutputPanel(QWidget):
    """输出区与底部状态标签。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("outputPanel")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        out_lbl = QLabel("输出")
        out_lbl.setMinimumWidth(36)
        layout.addWidget(out_lbl)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setMinimumHeight(200)
        layout.addWidget(self.output)

        self._status_label = QLabel("就绪。请连接设备并开启 USB 调试。")
        self._status_label.setObjectName("statusLabel")
        layout.addWidget(self._status_label)

    def _prepend_text(self, text: str):
        """在输出框顶部插入文本（倒序显示）。"""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.insertText(text + "\n")
        # 保持滚动在顶部
        self.output.moveCursor(QTextCursor.MoveOperation.Start)

    def append_output(self, code: int, out: str, err: str):
        # 倒序插入：先插入最后显示的内容
        lines = []
        lines.append("---")
        if out:
            lines.append(out.rstrip())
        if err:
            lines.append(f"[stderr] {err.rstrip()}")
        lines.append(f"[退出码: {code}]")
        # 反转顺序，因为每次都是插入到顶部
        self._prepend_text("\n".join(reversed(lines)))

    def append_step(self, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self._prepend_text(f"[{timestamp}] {msg}")

    def set_status(self, msg: str):
        self._status_label.setText(msg)
