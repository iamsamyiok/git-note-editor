from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMenu, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont
from datetime import datetime
from task_manager import TaskManager
from reminder_model import TriggerType
from reminder_scheduler import ReminderScheduler
from reminder_dialog import ReminderDialog
from task_dialog import TaskDialog


class TaskItemWidget(QWidget):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        content_label = QLabel(self.task.content)
        content_font = QFont()
        content_font.setPointSize(11)
        content_font.setBold(True)
        content_label.setFont(content_font)
        layout.addWidget(content_label)

        time_text = self._get_time_text()
        time_label = QLabel(time_text)
        time_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(time_label)

        self.setLayout(layout)

        if self.task.is_soon():
            self.setStyleSheet("background-color: #fff3cd; border-radius: 5px; padding: 5px;")

    def _get_time_text(self):
        type_names = {
            "once": "一次性",
            "daily": "每日",
            "weekly": "每周"
        }

        trigger_time = self.task.next_trigger.strftime("%m-%d %H:%M")
        type_name = type_names.get(self.task.trigger_type.value, "未知")

        if self.task.trigger_type == TriggerType.WEEKLY and self.task.weekdays:
            weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
            selected_days = ", ".join([weekday_names[d] for d in sorted(self.task.weekdays)])
            return f"{type_name} | {selected_days} {self.task.trigger_time.strftime('%H:%M')} | 下次: {trigger_time}"
        else:
            return f"{type_name} | 下次: {trigger_time}"


class ReminderWidget(QWidget):
    status_update = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_manager = TaskManager()
        self.scheduler = ReminderScheduler(self.task_manager)
        self.scheduler.task_triggered.connect(self.on_task_triggered)
        self.setup_ui()
        self.refresh_tasks()

    def setup_ui(self):
        layout = QVBoxLayout()

        toolbar = QHBoxLayout()

        add_btn = QPushButton("+ 添加任务")
        add_btn.setMinimumHeight(40)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        add_btn.clicked.connect(self.on_add_task)
        toolbar.addWidget(add_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.task_list = QListWidget()
        self.task_list.setAlternatingRowColors(True)
        self.task_list.setSelectionMode(QListWidget.SingleSelection)
        self.task_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.task_list)

        self.setLayout(layout)

    def refresh_tasks(self):
        self.task_list.clear()
        tasks = self.task_manager.get_all_tasks()

        if not tasks:
            empty_label = QListWidgetItem("暂无任务")
            empty_label.setTextAlignment(Qt.AlignCenter)
            empty_label.setForeground(QBrush(QColor("#999")))
            self.task_list.addItem(empty_label)
        else:
            for task in tasks:
                item = QListWidgetItem()
                widget = TaskItemWidget(task)
                item.setSizeHint(widget.sizeHint())
                self.task_list.addItem(item)
                self.task_list.setItemWidget(item, widget)

    def on_add_task(self):
        dialog = TaskDialog(parent=self)
        if dialog.exec_() == TaskDialog.Accepted:
            task_data = dialog.get_task_data()
            if task_data:
                task = self.task_manager.create_task(
                    task_data["content"],
                    task_data["trigger_type"],
                    task_data["trigger_time"],
                    task_data["weekdays"]
                )

                if task:
                    self.refresh_tasks()
                    self.status_update.emit("任务已创建")
                else:
                    QMessageBox.warning(self, "错误", "创建任务失败，请检查输入")

    def on_edit_task(self, task_id):
        task = self.task_manager.get_task(task_id)
        if not task:
            return

        dialog = TaskDialog(task, parent=self)
        if dialog.exec_() == TaskDialog.Accepted:
            task_data = dialog.get_task_data()
            if task_data:
                updated_task = self.task_manager.update_task(
                    task_id,
                    task_data["content"],
                    task_data["trigger_type"],
                    task_data["trigger_time"],
                    task_data["weekdays"]
                )

                if updated_task:
                    self.refresh_tasks()
                    self.status_update.emit("任务已更新")
                else:
                    QMessageBox.warning(self, "错误", "更新任务失败，请检查输入")

    def on_delete_task(self, task_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个任务吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.task_manager.delete_task(task_id):
                self.refresh_tasks()
                self.status_update.emit("任务已删除")
            else:
                QMessageBox.warning(self, "错误", "删除任务失败")

    def show_context_menu(self, pos):
        item = self.task_list.itemAt(pos)
        if not item or not self.task_list.itemWidget(item):
            return

        task_widget = self.task_list.itemWidget(item)
        task = task_widget.task

        menu = QMenu(self)

        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(lambda: self.on_edit_task(task.id))

        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.on_delete_task(task.id))

        menu.exec_(self.task_list.mapToGlobal(pos))

    def on_task_triggered(self, task):
        dialog = ReminderDialog(task, parent=self)
        dialog.action_triggered.connect(self.on_dialog_action)

        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()

        dialog.exec_()

    def on_dialog_action(self, task_id, action):
        if action == "snooze":
            self.task_manager.snooze_task(task_id)
            self.status_update.emit("任务已延后 5 分钟")
        elif action == "complete":
            if self.task_manager.get_task(task_id).trigger_type == TriggerType.ONCE:
                self.refresh_tasks()
            self.status_update.emit("任务已完成")

    def start_scheduler(self):
        self.scheduler.start()

    def stop_scheduler(self):
        self.scheduler.stop()