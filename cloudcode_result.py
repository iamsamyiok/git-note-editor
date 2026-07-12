from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor, QTextBlock

from cloudcode_executor import CloudCodeTask, TaskStatus


class CloudCodeResultDialog(QDialog):
    def __init__(self, task: CloudCodeTask, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Cloud Code 执行结果")
        self.setMinimumSize(700, 500)
        self._init_ui()
        self._display_result()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        if self.task.status == TaskStatus.COMPLETED:
            status_icon = "✅"
            status_text = "任务执行成功"
            status_color = "#28a745"
        elif self.task.status == TaskStatus.FAILED:
            status_icon = "❌"
            status_text = "任务执行失败"
            status_color = "#dc3545"
        elif self.task.status == TaskStatus.CANCELLED:
            status_icon = "⚠️"
            status_text = "任务已取消"
            status_color = "#ffc107"
        else:
            status_icon = "❓"
            status_text = "任务状态未知"
            status_color = "#6c757d"
        
        status_label = QLabel(f"{status_icon} {status_text}")
        status_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        status_label.setStyleSheet(f"color: {status_color};")
        header_layout.addWidget(status_label)
        
        header_layout.addStretch()
        
        copy_btn = QPushButton("📋 一键复制结果")
        copy_btn.clicked.connect(self._copy_result)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        header_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        info_group = QGroupBox("任务信息")
        info_layout = QVBoxLayout()
        
        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("任务描述："))
        desc_label = QLabel(self.task.description)
        desc_label.setWordWrap(True)
        desc_row.addWidget(desc_label)
        info_layout.addLayout(desc_row)
        
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("项目路径："))
        path_label = QLabel(self.task.project_path)
        path_label.setWordWrap(True)
        path_row.addWidget(path_label)
        info_layout.addLayout(path_row)
        
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("执行时间："))
        time_label = QLabel(f"{self.task.start_time} - {self.task.end_time}")
        time_row.addWidget(time_label)
        info_layout.addLayout(time_row)
        
        if self.task.exit_code is not None:
            code_row = QHBoxLayout()
            code_row.addWidget(QLabel("退出码："))
            code_text = str(self.task.exit_code)
            code_label = QLabel(code_text)
            if self.task.exit_code == 0:
                code_label.setStyleSheet("color: #28a745;")
            else:
                code_label.setStyleSheet("color: #dc3545;")
            code_row.addWidget(code_label)
            info_layout.addLayout(code_row)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        output_group = QGroupBox("执行输出")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        output_text.setStyleSheet("background: #f8f9fa;")
        output_layout.addWidget(self.output_text)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
    
    def _display_result(self):
        output = ""
        
        if self.task.stdout:
            output += "标准输出：\n" + self.task.stdout + "\n\n"
        
        if self.task.stderr:
            output += "错误输出：\n" + self.task.stderr
        
        if not output:
            output = "（无输出）"
        
        self.output_text.setText(output)
        self.output_text.moveCursor(QTextCursor.Start)
    
    def _copy_result(self):
        text = self.output_text.toPlainText()
        
        if text and text != "（无输出）":
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "成功", "结果已复制到剪贴板")
        else:
            QMessageBox.information(self, "提示", "没有可复制的内容")