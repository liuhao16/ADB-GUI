# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QDialogButtonBox,
)

class AppSelectionDialog(QDialog):
    """应用列表选择对话框，带搜索功能。"""
    
    def __init__(self, parent=None, packages=None):
        super().__init__(parent)
        self.setWindowTitle("选择应用")
        self.resize(500, 600)
        self._all_packages = packages or []

        layout = QVBoxLayout(self)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入包名过滤...")
        self.search_edit.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # 列表
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # 填充初始数据
        self._filter_list("")

        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _filter_list(self, text):
        self.list_widget.clear()
        text = text.lower()
        for pkg in self._all_packages:
            if text in pkg.lower():
                self.list_widget.addItem(pkg)

    def selected_package(self):
        items = self.list_widget.selectedItems()
        if items:
            return items[0].text()
        return None
