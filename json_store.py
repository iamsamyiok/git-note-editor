import os
import json
import tempfile
import logging

logger = logging.getLogger(__name__)


class JsonStore:
    """原子 JSON 读写工具。写入时先写临时文件再 rename，防止写入中断导致数据损坏。"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

    def read(self, default=None):
        """读取 JSON，失败时返回 default。"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"读取 {self.file_path} 失败: {e}")
            # 尝试读取备份
            bak = self.file_path + '.bak'
            if os.path.exists(bak):
                try:
                    with open(bak, 'r', encoding='utf-8') as f:
                        return json.load(f)
                    logger.info(f"从备份恢复 {self.file_path}")
                except Exception:
                    pass
        return default if default is not None else {}

    def write(self, data):
        """原子写入 JSON。先写临时文件，然后 rename 覆盖，并保留备份。"""
        dir_path = os.path.dirname(self.file_path) or '.'
        os.makedirs(dir_path, exist_ok=True)

        # 先备份当前文件
        if os.path.exists(self.file_path):
            try:
                import shutil
                shutil.copy2(self.file_path, self.file_path + '.bak')
            except Exception as e:
                logger.warning(f"创建备份失败: {e}")

        # 原子写：写临时文件 → rename
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.file_path)
        except Exception as e:
            logger.error(f"写入 {self.file_path} 失败: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
