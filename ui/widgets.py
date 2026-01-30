# -*- coding: utf-8 -*-
"""通用 UI 组件：标题栏、无边框对话框、消息框、输入框。"""

import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QLabel,
    QPushButton,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import (
    QMouseEvent,
    QPainter,
    QColor,
    QPainterPath,
    QPen,
    QBrush,
    QRegion,
)

# 圆角半径常量
RADIUS = 10


def apply_rounded_window_mask(widget: QWidget, radius: int = RADIUS) -> None:
    """对顶层窗口应用真正圆角裁剪（mask）。

    说明：QSS 的 border-radius 不会裁剪窗口形状，只是“看起来圆角”；
    这里用 setMask 把窗口区域裁剪成圆角矩形，避免四角“透出/直角边框”。
    """
    if hasattr(widget, "isMaximized") and widget.isMaximized():
        widget.clearMask()
        return
    if hasattr(widget, "isFullScreen") and widget.isFullScreen():
        widget.clearMask()
        return

    rect = QRectF(widget.rect())
    if rect.width() <= 0 or rect.height() <= 0:
        return
    path = QPainterPath()
    # 减少 0.5 像素的锯齿/偏移
    path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
    region = QRegion(path.toFillPolygon().toPolygon())
    widget.setMask(region)


class RoundedWidget(QWidget):
    """真正圆角的容器：通过 paintEvent 绘制圆角背景，而非 CSS border-radius。"""

    def __init__(self, parent=None, bg_color="#ffffff", border_color="#e4e4e7", radius=RADIUS):
        super().__init__(parent)
        self._bg_color = QColor(bg_color)
        self._border_color = QColor(border_color)
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_colors(self, bg_color: str, border_color: str):
        self._bg_color = QColor(bg_color)
        self._border_color = QColor(border_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角矩形背景
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        # 填充背景
        painter.fillPath(path, QBrush(self._bg_color))

        # 绘制边框
        painter.setPen(QPen(self._border_color, 1))
        painter.drawPath(path)


def try_enable_windows_acrylic(widget: QWidget) -> bool:
    """Windows 10/11：尽量启用原生亚克力/模糊；失败自动降级。"""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t),
            ]

        WCA_ACCENT_POLICY = 19
        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        ACCENT_ENABLE_BLURBEHIND = 3

        hwnd = int(widget.winId())
        # AABBGGRR：浅色主题 #ffffff -> BGR=0xffffff, alpha=0xE0
        gradient = 0xE0FFFFFF
        accent = ACCENTPOLICY(
            ACCENT_ENABLE_ACRYLICBLURBEHIND,
            0,
            gradient,
            0,
        )
        data = WINDOWCOMPOSITIONATTRIBDATA(
            WCA_ACCENT_POLICY,
            ctypes.cast(ctypes.byref(accent), ctypes.c_void_p),
            ctypes.sizeof(accent),
        )
        set_wca = ctypes.windll.user32.SetWindowCompositionAttribute
        ok = set_wca(wintypes.HWND(hwnd), ctypes.byref(data))
        if ok:
            return True

        accent2 = ACCENTPOLICY(ACCENT_ENABLE_BLURBEHIND, 0, gradient, 0)
        data2 = WINDOWCOMPOSITIONATTRIBDATA(
            WCA_ACCENT_POLICY,
            ctypes.cast(ctypes.byref(accent2), ctypes.c_void_p),
            ctypes.sizeof(accent2),
        )
        ok2 = set_wca(wintypes.HWND(hwnd), ctypes.byref(data2))
        return bool(ok2)
    except Exception:
        return False


class CustomTitleBar(QWidget):
    """无边框窗口的自定义标题栏，支持拖动、最小化、关闭。"""

    def __init__(self, parent: QMainWindow, title: str = ""):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._parent = parent
        self._drag_pos: QPoint | None = None
        self._setup_ui(title)
        self.setFixedHeight(40)

    def _setup_ui(self, title: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("titleLabel")
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self._title_label)

        layout.addStretch()

        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("btnMin")
        self.btn_min.setToolTip("最小化")
        self.btn_min.clicked.connect(self._on_minimize)
        layout.addWidget(self.btn_min)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btnClose")
        self.btn_close.setToolTip("关闭")
        self.btn_close.clicked.connect(self._on_close)
        layout.addWidget(self.btn_close)

    def set_title(self, title: str):
        self._title_label.setText(title)

    def _on_minimize(self):
        self._parent.showMinimized()

    def _on_close(self):
        self._parent.close()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self._parent.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._parent.isMaximized():
                self._parent.showNormal()
            else:
                self._parent.showMaximized()


class FramelessDialog(QDialog):
    """弹窗基类：恢复为系统原生窗口（直角/系统标题栏）。"""

    def __init__(self, parent, title: str = "", min_width: int = 300, min_height: int = 150):
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)

        self._content_widget = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(16)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._content_widget)

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def set_title(self, title: str):
        self.setWindowTitle(title)


class CustomMessageBox(FramelessDialog):
    """自定义消息框，替代 QMessageBox。"""

    OK = 1
    CANCEL = 2
    YES = 4
    NO = 8

    def __init__(self, parent, title: str, message: str, buttons: int = OK, icon_type: str = "info"):
        super().__init__(parent, title, min_width=360, min_height=140)
        self._result_button = None
        self._setup_ui(message, buttons, icon_type)

    def _setup_ui(self, message: str, buttons: int, icon_type: str):
        layout = self.content_layout()

        msg_layout = QHBoxLayout()
        msg_layout.setSpacing(12)

        icon_label = QLabel()
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "question": "❓",
            "error": "❌",
        }
        icon_label.setText(icon_map.get(icon_type, "ℹ️"))
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setFixedWidth(40)
        msg_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 10pt;")
        msg_layout.addWidget(msg_label, 1)

        layout.addLayout(msg_layout)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if buttons & self.OK:
            btn_ok = QPushButton("确定")
            btn_ok.setMinimumWidth(88)
            btn_ok.clicked.connect(lambda: self._on_button_clicked(self.OK))
            btn_layout.addWidget(btn_ok)

        if buttons & self.YES:
            btn_yes = QPushButton("是")
            btn_yes.setMinimumWidth(88)
            btn_yes.clicked.connect(lambda: self._on_button_clicked(self.YES))
            btn_layout.addWidget(btn_yes)

        if buttons & self.NO:
            btn_no = QPushButton("否")
            btn_no.setMinimumWidth(88)
            btn_no.clicked.connect(lambda: self._on_button_clicked(self.NO))
            btn_layout.addWidget(btn_no)

        if buttons & self.CANCEL:
            btn_cancel = QPushButton("取消")
            btn_cancel.setMinimumWidth(88)
            btn_cancel.clicked.connect(lambda: self._on_button_clicked(self.CANCEL))
            btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _on_button_clicked(self, button_type: int):
        self._result_button = button_type
        if button_type in (self.OK, self.YES):
            self.accept()
        else:
            self.reject()

    def result_button(self) -> int | None:
        return self._result_button

    @staticmethod
    def information(parent, title: str, message: str) -> int:
        dlg = CustomMessageBox(parent, title, message, CustomMessageBox.OK, "info")
        dlg.exec()
        return dlg.result_button() or CustomMessageBox.OK

    @staticmethod
    def warning(parent, title: str, message: str) -> int:
        dlg = CustomMessageBox(parent, title, message, CustomMessageBox.OK, "warning")
        dlg.exec()
        return dlg.result_button() or CustomMessageBox.OK

    @staticmethod
    def question(parent, title: str, message: str) -> int:
        dlg = CustomMessageBox(parent, title, message, CustomMessageBox.YES | CustomMessageBox.NO, "question")
        dlg.exec()
        return dlg.result_button() or CustomMessageBox.NO


class CustomInputDialog(FramelessDialog):
    """自定义输入框，替代 QInputDialog。"""

    def __init__(self, parent, title: str, label: str, default_text: str = ""):
        super().__init__(parent, title, min_width=400, min_height=160)
        self._text = ""
        self._ok = False
        self._setup_ui(label, default_text)

    def _setup_ui(self, label: str, default_text: str):
        layout = self.content_layout()

        lbl = QLabel(label)
        layout.addWidget(lbl)

        self._input = QLineEdit()
        self._input.setFixedHeight(40)
        self._input.setText(default_text)
        self._input.selectAll()
        layout.addWidget(self._input)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setMinimumWidth(88)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_ok = QPushButton("确定")
        btn_ok.setMinimumWidth(88)
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        self._input.returnPressed.connect(self._on_ok)

    def _on_ok(self):
        self._text = self._input.text()
        self._ok = True
        self.accept()

    def get_text(self) -> tuple[str, bool]:
        return self._text, self._ok

    @staticmethod
    def getText(parent, title: str, label: str, default_text: str = "") -> tuple[str, bool]:
        dlg = CustomInputDialog(parent, title, label, default_text)
        dlg.exec()
        return dlg.get_text()
