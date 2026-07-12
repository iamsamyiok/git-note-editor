import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class CloudCodeTaskDialog(QDialog):
    def __init__(self, project_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cloud Code 任务执行")
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        desc_label = QLabel("任务描述：")
        layout.addWidget(desc_label)
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "描述你要完成的任务，例如：\n"
            "- 创建一个简单的博客应用\n"
            "- 在 src 目录添加 utils.py 工具文件\n"
            "- 添加基本的单元测试"
        )
        self.desc_input.setMaximumHeight(100)
        layout.addWidget(self.desc_input)
        
        path_label = QLabel("项目路径：")
        layout.addWidget(path_label)
        
        path_row = QHBoxLayout()
        self.path_input = QLineEdit(project_path)
        path_row.addWidget(self.path_input)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_path)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)
        
        hint_label = QLabel("💡 提示：每次执行都会创建新的 Claude Code 会话")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("🚀 执行任务")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if path:
            self.path_input.setText(path)
    
    def get_task_data(self):
        return {
            'description': self.desc_input.toPlainText().strip(),
            'project_path': self.path_input.text().strip()
        }
    
    def accept(self):
        desc = self.desc_input.toPlainText().strip()
        path = self.path_input.text().strip()
        
        if not desc:
            QMessageBox.warning(self, "提示", "请输入任务描述")
            return
        
        if not path:
            QMessageBox.warning(self, "提示", "请选择项目路径")
            return
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "错误", "项目路径不存在")
            return
        
        if not os.path.isdir(path):
            QMessageBox.warning(self, "错误", "项目路径不是有效的目录")
            return
        
        super().accept()