from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTimeEdit, QCheckBox, QMessageBox,
    QGroupBox, QButtonGroup, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime, time
from reminder_model import TriggerType


class TaskDialog(QDialog):
    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("添加任务" if task is None else "编辑任务")
        self.setMinimumSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        content_label = QLabel("任务内容:")
        content_font = QFont()
        content_font.setPointSize(11)
        content_font.setBold(True)
        content_label.setFont(content_font)
        layout.addWidget(content_label)

        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("请输入任务内容...")
        self.content_edit.setMinimumHeight(35)
        if self.task:
            self.content_edit.setText(self.task.content)
        layout.addWidget(self.content_edit)

        type_group = QGroupBox("提醒类型")
        type_layout = QVBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["一次性", "每日", "每周"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        time_group = QGroupBox("提醒时间")
        time_layout = QHBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setCurrentSectionIndex(1)
        default_time = time(9, 0)
        self.time_edit.setTime(default_time)
        if self.task:
            self.time_edit.setTime(self.task.trigger_time)
        time_layout.addWidget(QLabel("时间:"))
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)

        self.weekday_group = QGroupBox("重复周期 (每周)")
        self.weekday_group.setVisible(False)
        weekday_layout = QGridLayout()
        self.weekday_checkboxes = []
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        for i, name in enumerate(weekday_names):
            checkbox = QCheckBox(name)
            if self.task and i in self.task.weekdays:
                checkbox.setChecked(True)
            self.weekday_checkboxes.append(checkbox)
            weekday_layout.addWidget(checkbox, i // 2, i % 2)

        self.weekday_group.setLayout(weekday_layout)
        layout.addWidget(self.weekday_group)

        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        save_btn.clicked.connect(self.on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        if self.task:
            index = ["once", "daily", "weekly"].index(self.task.trigger_type.value)
            self.type_combo.setCurrentIndex(index)

    def on_type_changed(self, index):
        is_weekly = (index == 2)
        self.weekday_group.setVisible(is_weekly)

    def get_task_data(self):
        content = self.content_edit.text().strip()
        if not content:
            QMessageBox.warning(self, "错误", "任务内容不能为空")
            return None

        trigger_time = self.time_edit.time().toPyTime()

        type_mapping = {
            0: TriggerType.ONCE,
            1: TriggerType.DAILY,
            2: TriggerType.WEEKLY
        }

        trigger_type = type_mapping[self.type_combo.currentIndex()]

        weekdays = []
        if trigger_type == TriggerType.WEEKLY:
            for i, checkbox in enumerate(self.weekday_checkboxes):
                if checkbox.isChecked():
                    weekdays.append(i)

            if not weekdays:
                QMessageBox.warning(self, "错误", "请至少选择一天")
                return None

        return {
            "content": content,
            "trigger_type": trigger_type,
            "trigger_time": trigger_time,
            "weekdays": weekdays
        }

    def on_save(self):
        task_data = self.get_task_data()
        if task_data:
            self.accept()