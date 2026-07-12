from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime


class ReminderDialog(QDialog):
    action_triggered = pyqtSignal(str, str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("任务提醒")
        self.setMinimumSize(500, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        content_frame = QFrame()
        content_frame.setFrameStyle(QFrame.StyledPanel)
        content_layout = QVBoxLayout(content_frame)

        title_label = QLabel("任务提醒")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setPlainText(self.task.content)
        content_font = QFont()
        content_font.setPointSize(12)
        content_text.setFont(content_font)
        content_layout.addWidget(content_text)

        info_label = QLabel(self._get_task_info())
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #666;")
        content_layout.addWidget(info_label)

        layout.addWidget(content_frame)

        button_layout = QHBoxLayout()

        snooze_btn = QPushButton("稍后提醒 (5分钟)")
        snooze_btn.setMinimumHeight(40)
        snooze_btn.clicked.connect(self.on_snooze)
        button_layout.addWidget(snooze_btn)

        complete_btn = QPushButton("标记完成")
        complete_btn.setMinimumHeight(40)
        complete_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        complete_btn.clicked.connect(self.on_complete)
        button_layout.addWidget(complete_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _get_task_info(self):
        trigger_type_names = {
            "once": "一次性",
            "daily": "每日",
            "weekly": "每周"
        }

        type_name = trigger_type_names.get(self.task.trigger_type.value, "未知")

        if self.task.trigger_type.value == "weekly" and self.task.weekdays:
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            selected_days = ", ".join([weekday_names[d] for d in sorted(self.task.weekdays)])
            return f"{type_name} | 时间: {self.task.trigger_time.strftime('%H:%M')} | 重复: {selected_days}"
        else:
            return f"{type_name} | 时间: {self.task.trigger_time.strftime('%H:%M')}"

    def on_snooze(self):
        self.action_triggered.emit(self.task.id, "snooze")
        self.accept()

    def on_complete(self):
        self.action_triggered.emit(self.task.id, "complete")
        self.accept()

    def closeEvent(self, event):
        self.action_triggered.emit(self.task.id, "dismiss")
        event.accept()