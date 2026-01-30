# -*- coding: utf-8 -*-
"""ADB 快捷操作 - 入口。"""

import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QIcon

from ui.theme import apply_modern_theme
from ui.main_window import MainWindow


def _icon_path() -> Path:
    """开发时用项目根目录的图标，打包后使用 _MEIPASS 内的 adb.ico。"""
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    # 优先 .ico（与 exe 图标一致），若无则用 .png
    ico = base / "adb.ico"
    if ico.is_file():
        return ico
    return base / "adb.png"


def _enable_high_dpi():
    """高 DPI 支持：Windows 下声明 DPI 感知，并设置 Qt 缩放策略。"""
    if os.name == "nt":
        try:
            import ctypes
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        except Exception:
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.Round
        )
    except Exception:
        pass


if __name__ == "__main__":
    _enable_high_dpi()
    app = QApplication(sys.argv)
    icon_path = _icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyle("Fusion")
    apply_modern_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
