# -*- coding: utf-8 -*-
"""shadcn 风格浅色主题 — 配色与对齐统一。"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


# ========== shadcn :root 浅色（Tailwind 精确 hex） ==========
# https://ui.shadcn.com/themes — 默认 light
BACKGROUND = "#ffffff"
CARD = "#ffffff"
FOREGROUND = "#09090b"           # zinc-950，更深对比
PRIMARY = "#ea580c"              # orange-600，主色
PRIMARY_FOREGROUND = "#ffffff"
PRIMARY_HOVER = "#c2410c"        # orange-700 悬停
SECONDARY = "#f4f4f5"            # zinc-100
SECONDARY_FOREGROUND = "#09090b"
MUTED = "#f4f4f5"
MUTED_FOREGROUND = "#71717a"     # zinc-500
ACCENT = "#f4f4f5"
ACCENT_FOREGROUND = "#09090b"
BORDER = "#e4e4e7"               # zinc-200
INPUT = "#e4e4e7"
RING = "#ea580c"                 # 焦点环与 primary 一致
# 参考图：关闭按钮悬停/按下 — 明亮红 + 白 X
DESTRUCTIVE = "#E81123"          # Windows 窗口关闭红
DESTRUCTIVE_PRESSED = "#C42B1C"  # 按下稍深

# 统一尺寸（shadcn --radius: 0.65rem）
RADIUS = "10px"
RADIUS_SM = "6px"
# 所有可交互控件统一高度，对齐一致
CONTROL_HEIGHT = "40px"


def apply_modern_theme(app: QApplication) -> None:
    """应用 shadcn 风格浅色主题，控件高度与对齐统一。"""
    try:
        app.setFont(QFont("Segoe UI", 10))
    except Exception:
        pass

    app.setStyleSheet(
        f"""
        /* ========== 主窗口/弹窗：恢复为原生直角窗口 ========== */
        QMainWindow {{
            background: {BACKGROUND};
        }}
        QWidget#container {{
            background: {BACKGROUND};
        }}
        QWidget#central {{
            background: {CARD};
            border: none;
        }}

        QDialog {{
            background: {BACKGROUND};
        }}

        /* ========== 标题栏 ========== */
        QWidget#titleBar {{
            /* 重要：避免标题栏矩形背景盖住顶部圆角 */
            background: transparent;
            border: none;
            border-bottom: 1px solid {BORDER};
        }}
        QWidget#titleBar QLabel {{
            color: {FOREGROUND};
            font-weight: 600;
            font-size: 10pt;
        }}
        /* 三键：默认白底/深色图标，圆角方形 */
        QWidget#titleBar QPushButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: #383838;
            font-size: 10pt;
            font-weight: normal;
            min-width: 46px;
            max-width: 46px;
            min-height: 32px;
            max-height: 32px;
            padding: 0;
        }}
        QWidget#titleBar QPushButton:hover {{
            background: #e5e5e5;
            color: #000000;
        }}
        QWidget#titleBar QPushButton:pressed {{
            background: #cccccc;
            color: #000000;
        }}
        QWidget#titleBar QPushButton:focus {{
            outline: none;
        }}
        /* 最小化 / 最大化：悬停浅灰、按下更深灰 */
        QWidget#titleBar QPushButton#btnMin:hover,
        QWidget#titleBar QPushButton#btnMax:hover {{
            background: #e5e5e5;
            color: #000000;
        }}
        QWidget#titleBar QPushButton#btnMin:pressed,
        QWidget#titleBar QPushButton#btnMax:pressed {{
            background: #cccccc;
            color: #000000;
        }}
        /* 关闭：悬停/按下 — 明亮红底、白色 X（与参考图一致） */
        QWidget#titleBar QPushButton#btnClose:hover {{
            background: {DESTRUCTIVE};
            color: #ffffff;
        }}
        QWidget#titleBar QPushButton#btnClose:pressed {{
            background: {DESTRUCTIVE_PRESSED};
            color: #ffffff;
        }}

        /* ========== 文字 ========== */
        QLabel {{
            color: {FOREGROUND};
            background: transparent;
        }}

        /* ========== 分组框 ========== */
        QGroupBox {{
            border: 1px solid {BORDER};
            border-radius: {RADIUS};
            margin-top: 14px;
            padding: 14px 12px 12px 12px;
            padding-top: 20px;
            background: {CARD};
            font-weight: 500;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: {FOREGROUND};
            font-weight: 600;
            font-size: 10pt;
        }}

        /* ========== 输入框 & 下拉框（统一高度） ========== */
        QLineEdit, QComboBox {{
            border: 1px solid {INPUT};
            border-radius: {RADIUS_SM};
            background: {BACKGROUND};
            padding: 0 12px;
            min-height: {CONTROL_HEIGHT};
            max-height: {CONTROL_HEIGHT};
            color: {FOREGROUND};
            selection-background-color: {PRIMARY};
            selection-color: {PRIMARY_FOREGROUND};
        }}
        QLineEdit:hover, QComboBox:hover {{
            border: 1px solid {BORDER};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {RING};
        }}
        QComboBox::drop-down {{
            width: 0px;
            border: none;
            background: transparent;
        }}
        /* 弹出层容器（QComboBoxPrivateContainer/QFrame）不画边框，避免淡色直角外框 */
        QComboBox QFrame {{
            border: none;
            outline: none;
            background: transparent;
        }}
        QComboBox QAbstractItemView {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: {RADIUS};
            padding: 6px;
            outline: none;
            selection-background-color: {PRIMARY};
            selection-color: {PRIMARY_FOREGROUND};
        }}
        QComboBox QScrollArea {{
            border: none;
            outline: none;
            background: transparent;
        }}
        QComboBox QScrollArea QWidget {{
            border: none;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 32px;
            height: 32px;
            padding: 0 10px;
            margin: 2px 0;
            border-radius: {RADIUS_SM};
            color: {FOREGROUND};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: {PRIMARY};
            color: {PRIMARY_FOREGROUND};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background: {ACCENT};
            color: {ACCENT_FOREGROUND};
        }}
        QComboBox QListView {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: {RADIUS};
            padding: 6px;
            outline: none;
        }}
        QComboBox QListView QScrollBar:vertical {{
            border: none;
            border-radius: 4px;
        }}
        QComboBox QListView::item {{
            min-height: 32px;
            height: 32px;
            padding: 0 10px;
            margin: 2px 0;
            border-radius: {RADIUS_SM};
            color: {FOREGROUND};
        }}
        QComboBox QListView::item:selected {{
            background: {PRIMARY};
            color: {PRIMARY_FOREGROUND};
        }}
        QComboBox QListView::item:hover {{
            background: {ACCENT};
            color: {ACCENT_FOREGROUND};
        }}

        /* ========== 输出区 ========== */
        QTextEdit {{
            border: 1px solid {BORDER};
            border-radius: {RADIUS_SM};
            background: {MUTED};
            color: {FOREGROUND};
            padding: 6px 8px;
            selection-background-color: {PRIMARY};
            selection-color: {PRIMARY_FOREGROUND};
        }}

        /* ========== 按钮（统一高度） ========== */
        QPushButton {{
            border: 1px solid {BORDER};
            border-radius: {RADIUS_SM};
            background: {BACKGROUND};
            color: {FOREGROUND};
            padding: 0 16px;
            min-height: {CONTROL_HEIGHT};
            max-height: {CONTROL_HEIGHT};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: {SECONDARY};
            border: 1px solid {BORDER};
        }}
        QPushButton:pressed {{
            background: {MUTED};
        }}
        QPushButton:disabled {{
            color: {MUTED_FOREGROUND};
            background: {MUTED};
            border: 1px solid {BORDER};
        }}
        QPushButton#btnPrimary {{
            background: {PRIMARY};
            color: {PRIMARY_FOREGROUND};
            border: 1px solid {PRIMARY};
        }}
        QPushButton#btnPrimary:hover {{
            background: {PRIMARY_HOVER};
            border: 1px solid {PRIMARY_HOVER};
        }}
        QPushButton#btnPrimary:pressed {{
            background: {PRIMARY};
        }}

        /* ========== Tab 栏 ========== */
        QTabWidget::pane {{
            border: 1px solid {BORDER};
            border-radius: {RADIUS};
            background: {CARD};
            padding: 12px;
            outline: none;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {MUTED_FOREGROUND};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 10px 16px;
            margin-right: 0;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            color: {FOREGROUND};
            border-bottom: 2px solid {PRIMARY};
        }}
        QTabBar::tab:hover:!selected {{
            color: {FOREGROUND};
            background: {ACCENT};
        }}

        /* ========== 底部状态 ========== */
        QLabel#statusLabel {{
            color: {MUTED_FOREGROUND};
            font-size: 9pt;
            padding: 6px 0 0 0;
        }}

        /* ========== 滚动条 ========== */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER};
            border-radius: 4px;
            min-height: 32px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {MUTED_FOREGROUND};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        /* ========== 消息框 ========== */
        QMessageBox {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: {RADIUS};
            outline: none;
        }}
        QMessageBox QLabel {{
            color: {FOREGROUND};
        }}
        """
    )
