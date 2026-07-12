import subprocess
import threading
from datetime import datetime
from typing import Callable
from enum import Enum


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


class CloudCodeExecutor:
    def __init__(self):
        self.active_tasks = {}
        self.task_callbacks = {}
    
    def execute_task(
        self,
        task_id: str,
        description: str,
        project_path: str,
        callback: Callable
    ) -> bool:
        task = CloudCodeTask(task_id, description, project_path)
        
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
            self.task_callbacks[task_id] = callback
            
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
            callback(task_id, task)
            return False
    
    def _build_command(self, description: str, project_path: str):
        return [
            "claude",
            project_path,
            "--permission-mode", "bypassPermissions",
            "--print", description
        ]
    
    def _monitor_task(self, task_id: str):
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        
        while task.process.poll() is None:
            import time
            time.sleep(0.5)
        
        stdout, stderr = task.process.communicate()
        exit_code = task.process.returncode
        
        task.stdout = stdout
        task.stderr = stderr
        task.exit_code = exit_code
        task.end_time = datetime.now().strftime("%H:%M:%S")
        
        if exit_code == 0:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.FAILED
        
        if task_id in self.task_callbacks:
            callback = self.task_callbacks[task_id]
            callback(task_id, task)
    
    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        
        if task.status == TaskStatus.RUNNING:
            task.process.terminate()
            task.status = TaskStatus.CANCELLED
            return True
        
        return False
    
    def get_task(self, task_id: str) -> CloudCodeTask | None:
        return self.active_tasks.get(task_id)
    
    def is_running(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        return task.status == TaskStatus.RUNNING