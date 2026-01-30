# -*- coding: utf-8 -*-
"""设备路径浏览对话框：列出设备目录与文件，路径可编辑，可选文件或文件夹。"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from adb_helper import list_device_path


def _norm_path(p: str) -> str:
    """规范化路径：去掉末尾斜杠（根保持为 /）。"""
    p = (p or "/").strip().rstrip("/")
    return p or "/"


def _parent_path(p: str) -> str:
    """父路径。"""
    p = _norm_path(p)
    if p == "/":
        return "/"
    return str(Path(p).parent).replace("\\", "/") or "/"


# 与主题 CONTROL_HEIGHT 一致，便于与输入框、按钮对齐
_BAR_HEIGHT = 40


class DevicePathDialog(QDialog):
    """设备路径选择对话框：浏览设备目录，路径可编辑，可选择文件或文件夹。"""
    path_selected = pyqtSignal(str)

    def __init__(self, parent, device: str, initial_path: str = "/sdcard", mode: str = "pull"):
        super().__init__(parent)
        self._device = device
        self._mode = mode  # "pull" 可选文件或文件夹；"push" 选目标文件夹
        self._current_path = _norm_path(initial_path)
        self._selected_path: str | None = None
        self._selected_is_dir = True
        self.setWindowTitle("选择设备路径" if mode == "pull" else "选择目标文件夹")
        self.setMinimumSize(520, 420)
        self.resize(560, 460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 路径说明
        path_lbl = QLabel("当前路径（可编辑，回车或点击「前往」刷新）：")
        layout.addWidget(path_lbl)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("/storage/emulated/0")
        self._path_edit.setClearButtonEnabled(True)
        self._path_edit.setFixedHeight(_BAR_HEIGHT)
        self._path_edit.setText(self._current_path)
        self._path_edit.returnPressed.connect(self._go_to_edit_path)
        path_row.addWidget(self._path_edit)

        btn_go = QPushButton("前往")
        btn_go.setObjectName("btnPrimary")
        btn_go.setFixedHeight(_BAR_HEIGHT)
        btn_go.clicked.connect(self._go_to_edit_path)
        path_row.addWidget(btn_go)
        layout.addLayout(path_row)

        # 文件列表
        list_lbl = QLabel("文件夹与文件（双击进入文件夹，选中后点「选择」）：")
        layout.addWidget(list_lbl)
        self._list = QListWidget()
        self._list.setFont(QFont("Consolas", 10))
        self._list.setMinimumHeight(220)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        # 底部三个按钮（统一高度、最小宽度、间距，右对齐与上方控件对齐）
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        _btn_min_w = 88
        btn_parent = QPushButton("上级目录")
        btn_parent.setFixedHeight(_BAR_HEIGHT)
        btn_parent.setMinimumWidth(_btn_min_w)
        btn_parent.clicked.connect(self._go_parent)
        btn_row.addWidget(btn_parent)
        btn_row.addSpacing(12)
        btn_select = QPushButton("选择")
        btn_select.setObjectName("btnPrimary")
        btn_select.setFixedHeight(_BAR_HEIGHT)
        btn_select.setMinimumWidth(_btn_min_w)
        btn_select.clicked.connect(self._on_select)
        btn_row.addWidget(btn_select)
        btn_row.addSpacing(12)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedHeight(_BAR_HEIGHT)
        btn_cancel.setMinimumWidth(_btn_min_w)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self._load_list()

    def _norm(self, p: str) -> str:
        return _norm_path(p)

    def _go_to_edit_path(self):
        raw = self._path_edit.text().strip()
        path = self._norm(raw or "/")
        self._path_edit.setText(path)
        self._navigate_to(path)

    def _navigate_to(self, path: str):
        path = self._norm(path)
        self._current_path = path
        self._path_edit.setText(path)
        self._load_list()

    def _go_parent(self):
        parent = _parent_path(self._current_path)
        self._navigate_to(parent)

    def _load_list(self):
        self._list.clear()
        entries, err = list_device_path(self._device, self._current_path)
        if err:
            self._list.addItem(QListWidgetItem(f"[错误] {err}"))
            return
        # 文件夹在前，然后文件；".." 放最前
        dirs = [e for e in entries if e["is_dir"] and e["name"] != ".."]
        files = [e for e in entries if not e["is_dir"]]
        up = [e for e in entries if e["name"] == ".."]
        for e in up:
            self._add_item(e)
        for e in sorted(dirs, key=lambda x: x["name"].lower()):
            self._add_item(e)
        for e in sorted(files, key=lambda x: x["name"].lower()):
            self._add_item(e)

    def _add_item(self, entry: dict):
        name = entry["name"]
        is_dir = entry["is_dir"]
        target = entry.get("target")
        item = QListWidgetItem(("📁 " if is_dir else "📄 ") + name)
        item.setData(Qt.ItemDataRole.UserRole, (name, is_dir, target))
        self._list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or ("", False, None)
        name, is_dir, target = data if len(data) >= 3 else (data[0], data[1], None)
        if name == "..":
            self._go_parent()
            return
        if is_dir:
            # 符号链接目录：进入目标路径，与手机文件管理显示一致
            if target:
                new_path = target.rstrip("/") or "/"
            else:
                new_path = f"{self._current_path.rstrip('/')}/{name}" if self._current_path != "/" else f"/{name}"
            self._navigate_to(new_path)

    def _on_selection_changed(self):
        item = self._list.currentItem()
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole) or ("", False, None)
        name, is_dir, target = data if len(data) >= 3 else (data[0], data[1], None)
        if name == "..":
            self._path_edit.setText(_parent_path(self._current_path))
            return
        if is_dir and target:
            self._path_edit.setText(target.rstrip("/") or "/")
        else:
            full = f"{self._current_path.rstrip('/')}/{name}" if self._current_path != "/" else f"/{name}"
            self._path_edit.setText(full)

    def _on_select(self):
        path = self._path_edit.text().strip()
        path = self._norm(path or self._current_path)
        self._selected_path = path
        item = self._list.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole) or ("", True, None)
            self._selected_is_dir = data[1] if len(data) >= 2 else True
        else:
            self._selected_is_dir = False
        self.path_selected.emit(path)
        self.accept()

    def selected_path(self) -> str | None:
        """对话框关闭后，若用户点了「选择」则返回选中的路径，否则为 None。"""
        return self._selected_path

    def selected_is_dir(self) -> bool:
        """选中项是否为文件夹（仅在 selected_path 非空时有效）。"""
        return getattr(self, "_selected_is_dir", True)
