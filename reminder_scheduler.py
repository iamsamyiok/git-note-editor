import sys
import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
from task_manager import TaskManager
from reminder_model import TriggerType
from reminder_dialog import ReminderDialog


class ReminderScheduler(QObject):
    task_triggered = pyqtSignal(object)

    def __init__(self, task_manager: TaskManager):
        super().__init__()
        self.task_manager = task_manager
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_tasks)
        self.active_tasks = set()
        self.sound_play_count = 0
        self.max_sound_plays = 3
        self.sound_timer = QTimer()
        self.sound_timer.timeout.connect(self.play_sound)

    def start(self):
        self.timer.start(60000)

    def stop(self):
        self.timer.stop()
        self.sound_timer.stop()

    def check_tasks(self):
        now = datetime.datetime.now()
        due_tasks = self.task_manager.get_due_tasks()

        for task in due_tasks:
            if task.id not in self.active_tasks and task.next_trigger <= now:
                self.active_tasks.add(task.id)
                self.trigger_task(task)

    def trigger_task(self, task):
        self.play_sound()
        self.task_triggered.emit(task)

    def play_sound(self):
        if self.sound_play_count < self.max_sound_plays:
            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except:
                    pass
            else:
                try:
                    QApplication.beep()
                except:
                    pass

            self.sound_play_count += 1
            self.sound_timer.start(2000)

    def stop_sound(self):
        self.sound_timer.stop()
        self.sound_play_count = 0

    def handle_task_action(self, task_id: str, action: str):
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)

        if action == "complete":
            self.task_manager.complete_task(task_id)
        elif action == "snooze":
            self.task_manager.snooze_task(task_id)

        self.stop_sound()