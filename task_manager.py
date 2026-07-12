import os
import json
import datetime
from typing import List, Optional
from reminder_model import ReminderTask, TriggerType


class TaskManager:
    def __init__(self, data_dir: str = None):
        self.tasks: List[ReminderTask] = []
        self.data_dir = data_dir or self._get_default_data_dir()
        self.tasks_file = os.path.join(self.data_dir, "tasks.json")
        self.load_tasks()

    @staticmethod
    def _get_default_data_dir() -> str:
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                return os.path.join(appdata, 'GitNoteEditor')
        else:
            home = os.environ.get('HOME', '')
            if home:
                return os.path.join(home, '.gitnoteeditor')

        return os.getcwd()

    def load_tasks(self) -> bool:
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [ReminderTask.from_dict(t) for t in data.get("tasks", [])]
            else:
                self.tasks = []
                self.save_tasks()
            return True
        except Exception as e:
            print(f"加载任务失败: {e}")
            self.tasks = []
            return False

    def save_tasks(self) -> bool:
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)

            data = {
                "tasks": [task.to_dict() for task in self.tasks]
            }

            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存任务失败: {e}")
            return False

    def create_task(self, content: str, trigger_type: TriggerType, trigger_time: datetime.time, weekdays: List[int] = None) -> Optional[ReminderTask]:
        if not content or not content.strip():
            return None

        if trigger_type == TriggerType.WEEKLY and (not weekdays or len(weekdays) == 0):
            return None

        task = ReminderTask.create(content, trigger_type, trigger_time, weekdays)

        if trigger_type == TriggerType.ONCE and task.next_trigger <= datetime.datetime.now():
            return None

        self.tasks.append(task)
        if not self.save_tasks():
            self.tasks.remove(task)
            return None

        return task

    def update_task(self, task_id: str, content: str = None, trigger_type: TriggerType = None, trigger_time: datetime.time = None, weekdays: List[int] = None) -> Optional[ReminderTask]:
        task = self.get_task(task_id)
        if not task:
            return None

        if content is not None:
            task.content = content

        if trigger_type is not None:
            task.trigger_type = trigger_type

        if trigger_time is not None:
            task.trigger_time = trigger_time

        if weekdays is not None:
            task.weekdays = weekdays

        if trigger_type == TriggerType.WEEKLY and (not task.weekdays or len(task.weekdays) == 0):
            return None

        task.calculate_next_trigger()

        if trigger_type == TriggerType.ONCE and task.next_trigger <= datetime.datetime.now():
            return None

        if not self.save_tasks():
            task.calculate_next_trigger()
            return None

        return task

    def delete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False

        self.tasks.remove(task)
        return self.save_tasks()

    def get_task(self, task_id: str) -> Optional[ReminderTask]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_all_tasks(self) -> List[ReminderTask]:
        return sorted(self.tasks, key=lambda t: t.next_trigger)

    def get_due_tasks(self) -> List[ReminderTask]:
        now = datetime.datetime.now()
        return [task for task in self.tasks if task.is_due()]

    def get_soon_tasks(self, hours: int = 24) -> List[ReminderTask]:
        return [task for task in self.tasks if task.is_soon(hours)]

    def complete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False

        if task.trigger_type == TriggerType.ONCE:
            return self.delete_task(task_id)
        else:
            task.calculate_next_trigger()
            return self.save_tasks()

    def snooze_task(self, task_id: str, minutes: int = 5) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False

        task.next_trigger = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        return self.save_tasks()