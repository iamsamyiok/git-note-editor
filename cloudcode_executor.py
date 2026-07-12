import subprocess
import threading
import time
from datetime import datetime
from typing import Callable, Optional
from enum import Enum

from PyQt5.QtCore import QObject, pyqtSignal


class TaskStatus(Enum):
    PENDING = "等待中"
    RUNNING = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"


class CloudCodeTask:
    def __init__(self, task_id: str, description: str, project_path: str):
        self.id = task_id
        self.description = description
        self.project_path = project_path
        self.status = TaskStatus.PENDING
        self.start_time = ""
        self.end_time = ""
        self.stdout = ""
        self.stderr = ""
        self.exit_code = None
        self.process = None

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'project_path': self.project_path,
            'status': self.status.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'exit_code': self.exit_code
        }


class CloudCodeExecutor(QObject):
    # 跨线程安全信号：在子线程中 emit，Qt 会自动通过队列连接
    # 把槽函数调用派发到主线程执行，避免在子线程中直接操作 Qt 控件导致崩溃。
    task_completed = pyqtSignal(str, object)

    # 已终结任务保留数量上限
    MAX_COMPLETED_TASKS = 20
    # 默认任务超时（秒）
    DEFAULT_TIMEOUT = 600

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_tasks = {}
        self.timeout = self.DEFAULT_TIMEOUT

    def execute_task(
        self,
        task_id: str,
        description: str,
        project_path: str,
        callback: Optional[Callable] = None
    ) -> bool:
        task = CloudCodeTask(task_id, description, project_path)

        # 通过 pyqtSignal 桥接跨线程回调：调用方传入的 callback 通常会直接
        # 操作 Qt Widget（QMessageBox、QDialog 等），不能在子线程中直接调用。
        # 这里把 callback 包装成一次性槽，仅处理本任务，触发后自动断开连接，
        # 避免并发任务互相触发或多次累积连接。
        if callback is not None:
            def _one_shot(tid, t):
                if tid != task_id:
                    return
                try:
                    callback(tid, t)
                finally:
                    try:
                        self.task_completed.disconnect(_one_shot)
                    except Exception:
                        pass

            self.task_completed.connect(_one_shot)

        command = self._build_command(description, project_path)

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_path
            )

            task.process = process
            task.status = TaskStatus.RUNNING
            task.start_time = datetime.now().strftime("%H:%M:%S")

            self.active_tasks[task_id] = task

            monitor_thread = threading.Thread(
                target=self._monitor_task,
                args=(task_id,),
                daemon=True
            )
            monitor_thread.start()

            return True
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.stderr = str(e)
            task.end_time = datetime.now().strftime("%H:%M:%S")
            self.active_tasks[task_id] = task
            self.task_completed.emit(task_id, task)
            self._cleanup_tasks()
            return False

    def _build_command(self, description: str, project_path: str):
        # 使用 default 权限模式，避免 bypassPermissions 带来的安全风险
        return [
            "claude",
            project_path,
            "--permission-mode", "default",
            "--print", description
        ]

    def _monitor_task(self, task_id: str):
        if task_id not in self.active_tasks:
            return

        task = self.active_tasks[task_id]
        process = task.process

        stdout, stderr = "", ""
        try:
            # 直接用 communicate() 阻塞等待，它会内部并发读取 stdout/stderr
            # 两路管道，避免输出超过 64KB 管道缓冲区时死锁。
            stdout, stderr = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            # 超时则强制终止进程并回收剩余输出
            process.kill()
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                stdout, stderr = (stdout or ""), (stderr or "")

        task.stdout = stdout or ""
        task.stderr = stderr or ""
        task.exit_code = process.returncode
        task.end_time = datetime.now().strftime("%H:%M:%S")

        # 若任务已被 cancel_task 标记为 CANCELLED，则跳过状态更新，保持取消状态
        if task.status != TaskStatus.CANCELLED:
            if task.exit_code == 0:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED

        self.task_completed.emit(task_id, task)
        self._cleanup_tasks()

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]

        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            task.end_time = datetime.now().strftime("%H:%M:%S")
            try:
                task.process.terminate()
            except Exception:
                pass
            try:
                # 给进程 5 秒优雅退出时间，超时则强制 kill
                task.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    task.process.kill()
                except Exception:
                    pass
            return True

        return False

    def _cleanup_tasks(self):
        # 仅清理已终结的任务，保留最近 MAX_COMPLETED_TASKS 条
        finished_states = (
            TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED
        )
        finished_ids = [
            tid for tid, t in self.active_tasks.items()
            if t.status in finished_states
        ]
        while len(finished_ids) > self.MAX_COMPLETED_TASKS:
            tid = finished_ids.pop(0)
            self.active_tasks.pop(tid, None)

    def get_task(self, task_id: str) -> Optional[CloudCodeTask]:
        return self.active_tasks.get(task_id)

    def is_running(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        return task.status == TaskStatus.RUNNING
