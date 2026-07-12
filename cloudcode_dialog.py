import os
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor


# 任务描述最大长度
DESC_MAX_LENGTH = 2000
# 用于提供默认 project_path 的环境变量名
PROJECT_PATH_ENV = "CLOUDCODE_PROJECT_PATH"


class CloudCodeTaskDialog(QDialog):
    # 记录上次成功使用的项目路径，供下次打开对话框时作为默认值
    _last_project_path = ""

    def __init__(self, project_path="", parent=None):
        # project_path 默认值优先级：显式传参 > 环境变量 > 上次使用路径
        if not project_path:
            project_path = (
                os.environ.get(PROJECT_PATH_ENV, "")
                or CloudCodeTaskDialog._last_project_path
            )
        self._initial_project_path = project_path
        super().__init__(parent)
        self.setWindowTitle("Cloud Code 任务执行")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 安全警示
        warn_label = QLabel(
            "⚠️ Cloud Code 将在指定目录中执行 AI 任务，请确保信任任务描述"
        )
        warn_label.setStyleSheet("color: #dc3545; font-size: 11px;")
        warn_label.setWordWrap(True)
        layout.addWidget(warn_label)

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
        # QTextEdit 没有 setMaxLength，通过 textChanged 信号限制输入长度
        self.desc_input.textChanged.connect(self._limit_desc_length)
        layout.addWidget(self.desc_input)

        path_label = QLabel("项目路径：")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit(self._initial_project_path)
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

    def _limit_desc_length(self):
        # QTextEdit 无 maxLength 属性，手动截断到 DESC_MAX_LENGTH，
        # 截断后恢复光标位置以保持编辑体验。
        text = self.desc_input.toPlainText()
        if len(text) > DESC_MAX_LENGTH:
            cursor = self.desc_input.textCursor()
            pos = cursor.position()
            self.desc_input.blockSignals(True)
            self.desc_input.setPlainText(text[:DESC_MAX_LENGTH])
            self.desc_input.blockSignals(False)
            new_cursor = self.desc_input.textCursor()
            new_cursor.setPosition(min(pos, DESC_MAX_LENGTH))
            self.desc_input.setTextCursor(new_cursor)

    def _browse_path(self):
        start_dir = self.path_input.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "选择项目目录", start_dir)
        if path:
            self.path_input.setText(path)

    def _is_unsafe_path(self, path: str) -> bool:
        """校验路径是否落在禁止的目录（根目录 / 盘符根 / 家目录）"""
        if not path:
            return True
        norm = os.path.normpath(path)
        # 禁止 POSIX 根目录
        if norm == os.path.sep:
            return True
        # 禁止 Windows 盘符根目录，如 C:\ D:\ 等
        if re.match(r"^[A-Za-z]:[\\/]+$", norm):
            return True
        # 禁止家目录本身
        home = os.path.normpath(os.path.expanduser("~"))
        if norm == home:
            return True
        return False

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

        # 白名单校验：禁止在根目录、盘符根、家目录执行任务，避免误操作范围过大
        if self._is_unsafe_path(path):
            QMessageBox.warning(
                self, "安全限制",
                "出于安全考虑，不允许在根目录（/、C:\\）或家目录中执行 Cloud Code 任务。\n"
                "请选择具体的项目子目录。"
            )
            return

        # 记忆本次使用的路径，供下次作为默认值
        CloudCodeTaskDialog._last_project_path = path
        super().accept()
