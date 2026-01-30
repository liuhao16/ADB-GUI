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
    QTabWidget,
    QFormLayout,
    QSizePolicy,
)
import os
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QPoint
from PyQt6.QtGui import QFont, QPixmap, QImage, QIntValidator, QMouseEvent

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


def apply_modern_theme(app: QApplication):
    """全局现代紧凑主题（跨平台）- 全浅色风格，浅蓝强调。"""
    # 统一字体（Windows 下更贴近现代 UI）
    try:
        app.setFont(QFont("Segoe UI", 10))
    except Exception:
        pass

    # 配色变量 - 全浅色风格
    bg_main = "#f1f5f9"           # 浅灰蓝主背景
    bg_titlebar = "#e2e8f0"       # 标题栏背景（稍深一点的浅灰）
    bg_card = "#ffffff"           # 卡片/中央区域（纯白）
    bg_input = "#ffffff"          # 输入框
    bg_output = "#f8fafc"         # 输出区（浅色）
    text_primary = "#1e293b"      # 主文字（深色）
    text_secondary = "#64748b"    # 次要文字
    accent = "#3b82f6"            # 浅蓝色（强调色）
    accent_hover = "#2563eb"      # 悬停时的蓝
    accent_light = "#dbeafe"      # 浅蓝背景
    border_light = "#cbd5e1"      # 浅色边框
    border_focus = "#3b82f6"      # 聚焦边框

    app.setStyleSheet(
        f"""
        /* ========== 主窗口 & 弹窗 ========== */
        QMainWindow {{
            background: {bg_main};
        }}
        QDialog {{
            background: {bg_card};
            border: 1px solid {border_light};
            border-radius: 12px;
        }}
        QWidget#central {{
            background: {bg_card};
            border: none;
            border-radius: 0 0 12px 12px;
        }}

        /* ========== 自定义标题栏（浅色） ========== */
        QWidget#titleBar {{
            background: {bg_titlebar};
            border: none;
            border-radius: 12px 12px 0 0;
        }}
        QWidget#titleBar QLabel {{
            color: {text_primary};
            font-weight: 600;
            font-size: 11pt;
        }}
        QWidget#titleBar QPushButton {{
            background: transparent;
            border: none;
            border-radius: 6px;
            color: {text_secondary};
            font-size: 14px;
            font-weight: bold;
            min-width: 40px;
            max-width: 40px;
            min-height: 32px;
            max-height: 32px;
            padding: 0;
        }}
        QWidget#titleBar QPushButton:hover {{
            background: rgba(0, 0, 0, 0.08);
            color: {text_primary};
        }}
        QWidget#titleBar QPushButton#btnClose:hover {{
            background: #ef4444;
            color: white;
        }}
        QWidget#titleBar QPushButton#btnMin:hover {{
            background: rgba(0, 0, 0, 0.1);
        }}

        /* ========== 文字 ========== */
        QLabel {{
            color: {text_primary};
            background: transparent;
        }}

        /* ========== 分组框 ========== */
        QGroupBox {{
            border: 1px solid {border_light};
            border-radius: 10px;
            margin-top: 14px;
            padding-top: 8px;
            background: rgba(255, 255, 255, 0.9);
            font-weight: 500;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: {text_primary};
            font-weight: 600;
        }}

        /* ========== 输入框 & 下拉框 ========== */
        QLineEdit, QComboBox {{
            border: 1px solid {border_light};
            border-radius: 8px;
            background: {bg_input};
            padding: 7px 12px;
            color: {text_primary};
            selection-background-color: {accent};
            selection-color: white;
        }}
        QLineEdit:hover, QComboBox:hover {{
            border: 1px solid {accent};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {border_focus};
        }}
        QComboBox::drop-down {{
            border: 0px;
            width: 28px;
        }}
        QComboBox QAbstractItemView {{
            background: {bg_input};
            border: 1px solid {border_light};
            border-radius: 8px;
            selection-background-color: {accent};
            selection-color: white;
        }}

        /* ========== 输出区（浅色风格） ========== */
        QTextEdit {{
            border: 1px solid {border_light};
            border-radius: 10px;
            background: {bg_output};
            color: {text_primary};
            padding: 10px 12px;
            selection-background-color: {accent};
            selection-color: white;
        }}

        /* ========== 按钮 ========== */
        QPushButton {{
            border: 1px solid {border_light};
            border-radius: 8px;
            background: {bg_input};
            color: {text_primary};
            padding: 8px 16px;
            min-height: 32px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: {accent};
            color: white;
            border: 1px solid {accent};
        }}
        QPushButton:pressed {{
            background: {accent_hover};
            border: 1px solid {accent_hover};
        }}
        QPushButton:disabled {{
            color: {text_secondary};
            background: #f1f5f9;
            border: 1px solid {border_light};
        }}

        /* ========== Tab 栏 ========== */
        QTabWidget::pane {{
            border: 1px solid {border_light};
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 8px;
        }}
        QTabBar::tab {{
            background: #f1f5f9;
            color: {text_secondary};
            border: 1px solid {border_light};
            border-bottom: 0px;
            padding: 8px 16px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 4px;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            background: {bg_input};
            color: {text_primary};
            border: 1px solid {accent};
            border-bottom: 0px;
        }}
        QTabBar::tab:hover:!selected {{
            background: {accent_light};
            color: {text_primary};
        }}

        /* ========== 底部状态标签 ========== */
        QLabel#statusLabel {{
            color: {text_secondary};
            font-size: 9pt;
            padding: 4px 8px;
        }}

        /* ========== 滚动条 ========== */
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {border_light};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        /* ========== 消息框 ========== */
        QMessageBox {{
            background: {bg_card};
        }}
        QMessageBox QLabel {{
            color: {text_primary};
        }}
        """
    )


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

        # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowcompositionattribute (非官方文档化 API)
        WCA_ACCENT_POLICY = 19
        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        ACCENT_ENABLE_BLURBEHIND = 3

        hwnd = int(widget.winId())
        # GradientColor: AABBGGRR（ABGR 格式）。浅灰蓝 #f1f5f9 → BGR=0xf9f5f1，alpha=0xE0
        gradient = 0xE0F9F5F1
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

        # 退化为 blur behind
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


# ==================== 自定义标题栏 ====================


class CustomTitleBar(QWidget):
    """无边框窗口的自定义标题栏，支持拖动、最小化、关闭。"""

    def __init__(self, parent: QMainWindow, title: str = ""):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._parent = parent
        self._drag_pos: QPoint | None = None
        self._setup_ui(title)
        self.setFixedHeight(44)

    def _setup_ui(self, title: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(0)

        # 标题
        self._title_label = QLabel(title)
        self._title_label.setObjectName("titleLabel")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # 最小化按钮
        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("btnMin")
        self.btn_min.setToolTip("最小化")
        self.btn_min.clicked.connect(self._on_minimize)
        layout.addWidget(self.btn_min)

        # 关闭按钮
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

    # ---------- 拖动支持 ----------
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
        # 双击标题栏切换最大化/还原
        if event.button() == Qt.MouseButton.LeftButton:
            if self._parent.isMaximized():
                self._parent.showNormal()
            else:
                self._parent.showMaximized()


class FramelessDialog(QDialog):
    """无边框弹窗基类，自带自定义标题栏。"""

    def __init__(self, parent, title: str = "", min_width: int = 300, min_height: int = 150):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(min_width, min_height)

        # 外层容器
        self._container = QWidget(self)
        self._container.setObjectName("dialogContainer")
        self._container.setStyleSheet("""
            QWidget#dialogContainer {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
        """)

        # 主布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._container)

        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 自定义标题栏
        self._title_bar = CustomTitleBar(self, title)
        self._main_layout.addWidget(self._title_bar)

        # 内容区容器
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(16, 12, 16, 16)
        self._content_layout.setSpacing(12)
        self._main_layout.addWidget(self._content_widget)

    def content_layout(self) -> QVBoxLayout:
        """返回内容区布局，子类用于添加控件。"""
        return self._content_layout

    def set_title(self, title: str):
        self._title_bar.set_title(title)

    def showEvent(self, event):
        super().showEvent(event)
        try_enable_windows_acrylic(self)


class CustomMessageBox(FramelessDialog):
    """自定义消息框，替代 QMessageBox。"""

    # 按钮类型常量
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

        # 图标 + 消息
        msg_layout = QHBoxLayout()
        msg_layout.setSpacing(12)

        # 图标
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

        # 消息文本
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 10pt;")
        msg_layout.addWidget(msg_label, 1)

        layout.addLayout(msg_layout)
        layout.addStretch()

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if buttons & self.OK:
            btn_ok = QPushButton("确定")
            btn_ok.setMinimumWidth(80)
            btn_ok.clicked.connect(lambda: self._on_button_clicked(self.OK))
            btn_layout.addWidget(btn_ok)

        if buttons & self.YES:
            btn_yes = QPushButton("是")
            btn_yes.setMinimumWidth(80)
            btn_yes.clicked.connect(lambda: self._on_button_clicked(self.YES))
            btn_layout.addWidget(btn_yes)

        if buttons & self.NO:
            btn_no = QPushButton("否")
            btn_no.setMinimumWidth(80)
            btn_no.clicked.connect(lambda: self._on_button_clicked(self.NO))
            btn_layout.addWidget(btn_no)

        if buttons & self.CANCEL:
            btn_cancel = QPushButton("取消")
            btn_cancel.setMinimumWidth(80)
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

    # ---------- 静态方法（替代 QMessageBox） ----------
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

        # 标签
        lbl = QLabel(label)
        layout.addWidget(lbl)

        # 输入框
        self._input = QLineEdit()
        self._input.setText(default_text)
        self._input.selectAll()
        layout.addWidget(self._input)

        layout.addStretch()

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.setMinimumWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_ok = QPushButton("确定")
        btn_ok.setMinimumWidth(80)
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        # 回车确认
        self._input.returnPressed.connect(self._on_ok)

    def _on_ok(self):
        self._text = self._input.text()
        self._ok = True
        self.accept()

    def get_text(self) -> tuple[str, bool]:
        return self._text, self._ok

    # ---------- 静态方法（替代 QInputDialog.getText） ----------
    @staticmethod
    def getText(parent, title: str, label: str, default_text: str = "") -> tuple[str, bool]:
        dlg = CustomInputDialog(parent, title, label, default_text)
        dlg.exec()
        return dlg.get_text()


class PairingDialog(FramelessDialog):
    """显示供手机扫描的二维码，监听 mDNS，手机扫码后自动执行 adb pair。"""
    pairing_success = pyqtSignal()
    log_step = pyqtSignal(str)  # 步骤说明，由主窗口输出到输出区
    command_output = pyqtSignal(int, str, str)  # 配对/连接命令的 code, out, err，由主窗口追加到输出区

    def __init__(self, parent: QMainWindow):
        super().__init__(parent, "手机扫码连接", min_width=340, min_height=420)
        self._main_parent = parent
        self._notifier = PairingNotifier(self)
        self._zeroconf_thread: ZeroconfThread | None = None
        self._pair_worker: Worker | None = None
        self._paired = False
        # 随机六位数字作为配对码
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


def _is_success_connect_output(out: str) -> bool:
    s = (out or "").lower()
    return ("connected to " in s) or ("already connected to " in s)


def _is_success_pair_output(out: str) -> bool:
    return "Successfully paired" in (out or "")


def _pair_then_connect(pair_host: str, pair_port: int, code: str, connect_host: str, connect_port: int):
    code1, out1, err1 = adb_pair(pair_host, pair_port, code)
    if code1 != 0 or not _is_success_pair_output(out1):
        return code1, f"[pair]\n{out1}", f"[pair stderr]\n{err1}"
    code2, out2, err2 = run_adb("connect", f"{connect_host}:{connect_port}", timeout=15)
    out = "\n\n".join([x for x in ["[pair]\n" + (out1 or "").rstrip(), "[connect]\n" + (out2 or "").rstrip()] if x.strip()])
    err = "\n\n".join([x for x in ["[pair stderr]\n" + (err1 or "").rstrip(), "[connect stderr]\n" + (err2 or "").rstrip()] if x.strip()])
    return code2, out, err


def _connect_only(host: str, port: int):
    return run_adb("connect", f"{host}:{port}", timeout=15)


class ManualConnectDialog(FramelessDialog):
    """手动输入 IP 连接：支持配对+连接 或 仅连接。"""

    connect_requested = pyqtSignal(str, dict)  # mode, payload

    def __init__(self, parent: QMainWindow):
        super().__init__(parent, "手动连接", min_width=440, min_height=320)
        self._tabs = None
        self._setup_content()

    def _setup_content(self):
        layout = self.content_layout()

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- Tab A: 配对 + 连接 ---
        tab_pair = QWidget()
        form_pair = QFormLayout(tab_pair)
        form_pair.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_pair.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.pair_ip = QLineEdit()
        self.pair_ip.setPlaceholderText("例如 192.168.1.10")
        self.pair_port = QLineEdit()
        self.pair_port.setText("37099")
        self.pair_port.setValidator(QIntValidator(1, 65535, self))
        self.pair_code = QLineEdit()
        self.pair_code.setPlaceholderText("6 位配对码")
        self.pair_code.setMaxLength(6)
        self.pair_code.setValidator(QIntValidator(0, 999999, self))
        self.conn_ip = QLineEdit()
        self.conn_ip.setPlaceholderText("默认同上，也可不同")
        self.conn_port = QLineEdit()
        self.conn_port.setText("5555")
        self.conn_port.setValidator(QIntValidator(1, 65535, self))

        form_pair.addRow("配对 IP：", self.pair_ip)
        form_pair.addRow("配对端口：", self.pair_port)
        form_pair.addRow("配对码：", self.pair_code)
        form_pair.addRow("连接 IP：", self.conn_ip)
        form_pair.addRow("连接端口：", self.conn_port)

        self._tabs.addTab(tab_pair, "配对+连接")

        # --- Tab B: 仅连接 ---
        tab_conn = QWidget()
        form_conn = QFormLayout(tab_conn)
        form_conn.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_conn.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.only_ip = QLineEdit()
        self.only_ip.setPlaceholderText("例如 192.168.1.10")
        self.only_port = QLineEdit()
        self.only_port.setText("5555")
        self.only_port.setValidator(QIntValidator(1, 65535, self))
        form_conn.addRow("IP：", self.only_ip)
        form_conn.addRow("端口：", self.only_port)

        self._tabs.addTab(tab_conn, "仅连接")

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton("取消")
        self.btn_ok = QPushButton("连接")
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(720, 560)
        self.resize(880, 640)
        self._worker = None
        self._device = ""
        self._auto_prompted_connect = False
        self._setup_ui()
        self._refresh_devices(allow_auto_prompt=True)

    def _setup_ui(self):
        # 外层容器（用于圆角和阴影）
        container = QWidget()
        container.setObjectName("container")
        container.setStyleSheet("""
            QWidget#container {
                background: transparent;
            }
        """)
        self.setCentralWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 自定义标题栏
        self._title_bar = CustomTitleBar(self, "ADB 快捷操作")
        main_layout.addWidget(self._title_bar)

        # 内容区
        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 12)

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
        self.btn_manual_connect = QPushButton("手动连接")
        self.btn_manual_connect.clicked.connect(self._on_manual_connect)
        dev_layout.addWidget(self.btn_manual_connect)
        dev_layout.addStretch()
        layout.addLayout(dev_layout)

        # 快捷操作区
        group = QGroupBox("快捷操作")
        group_layout = QGridLayout()
        group_layout.setHorizontalSpacing(8)
        group_layout.setVerticalSpacing(8)
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

        # 底部状态标签（替代系统状态栏）
        self._status_label = QLabel("就绪。请连接设备并开启 USB 调试。")
        self._status_label.setObjectName("statusLabel")
        layout.addWidget(self._status_label)

        main_layout.addWidget(central)

    def _set_status(self, msg: str):
        """设置底部状态消息。"""
        self._status_label.setText(msg)

    def _log_step(self, msg: str):
        """在输出区追加一步操作说明。"""
        self.output.append(f"[步骤] {msg}")
        self.output.ensureCursorVisible()

    def _on_device_changed(self, index):
        if index < 0:
            self._device = ""
            return
        self._device = self.device_combo.currentData() or ""

    def _refresh_devices(self, *, allow_auto_prompt: bool = False):
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
            self._set_status(f"已连接 {len(devices)} 台设备")
        else:
            self._device = ""
            self._log_step("未检测到设备")
            self._set_status("未检测到设备，请连接并开启 USB 调试")
            if allow_auto_prompt and not self._auto_prompted_connect:
                # 仅启动阶段自动弹一次；延迟触发避免窗口未显示时阻塞 UI
                self._auto_prompted_connect = True
                QTimer.singleShot(150, self._on_scan_connect)

    def _ensure_device(self) -> bool:
        if not self._device:
            CustomMessageBox.warning(self, "提示", "请先选择设备")
            return False
        return True

    def _on_scan_connect(self):
        """手机扫码连接：弹出二维码窗口，手机扫描后通过 mDNS 自动配对。"""
        self._log_step("打开扫码连接窗口")
        dlg = PairingDialog(self)
        dlg.log_step.connect(self._log_step)
        dlg.command_output.connect(self._append_output)
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
                _pair_then_connect,
                payload["pair_host"],
                payload["pair_port"],
                payload["code"],
                payload["connect_host"],
                payload["connect_port"],
            )
            return
        if mode == "connect_only":
            self._log_step(f"手动连接：连接 {payload['host']}:{payload['port']}")
            self._run_worker(_connect_only, payload["host"], payload["port"])
            return

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
            self._set_status("请等待当前命令执行完成")
            return
        self._worker = Worker(func, *args, **kwargs)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        self._log_step("命令执行中…")
        self._set_status("执行中...")
        self.btn_refresh.setEnabled(False)

    def _on_worker_finished(self, code: int, out: str, err: str):
        self.btn_refresh.setEnabled(True)
        self._log_step("命令执行完成")
        self._append_output(code, out, err)
        # 若是无线连接相关，成功时刷新设备列表
        out_text = out or ""
        if code == 0 and (
            _is_success_connect_output(out_text)
            or _is_success_pair_output(out_text)
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
        reply = CustomMessageBox.question(self, "确认", "是否重启设备？")
        if reply != CustomMessageBox.YES:
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
        remote, ok = CustomInputDialog.getText(self, "拉取文件", "设备路径 (如 /sdcard/xxx):")
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
        cmd, ok = CustomInputDialog.getText(self, "Shell 命令", "输入 shell 命令:")
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
    apply_modern_theme(app)
    win = MainWindow()
    win.show()
    QTimer.singleShot(0, lambda: try_enable_windows_acrylic(win))
    sys.exit(app.exec())
