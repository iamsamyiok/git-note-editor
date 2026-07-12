from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QProgressBar, QTextEdit,
)
from PyQt5.QtCore import Qt


class CommitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提交变更")
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("请输入本次提交摘要："))

        self.msg_edit = QTextEdit()
        self.msg_edit.setPlaceholderText("描述本次修改内容...")
        self.msg_edit.setMaximumHeight(100)
        layout.addWidget(self.msg_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("提交")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def commit_message(self) -> str:
        return self.msg_edit.toPlainText().strip()

    def _on_ok(self):
        if not self.commit_message():
            return
        self.accept()


class BranchDialog(QDialog):
    def __init__(self, existing_names, parent=None):
        super().__init__(parent)
        self.existing = set(existing_names)
        self.setWindowTitle("新建分支")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("分支名称："))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入分支名称（支持中文、空格、特殊字符）")
        self.name_edit.textChanged.connect(self._validate)
        layout.addWidget(self.name_edit)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.ok_btn = QPushButton("创建")
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)

    def branch_name(self) -> str:
        return self.name_edit.text().strip()

    def _validate(self):
        name = self.branch_name()
        if not name:
            self.error_label.setText("")
            self.ok_btn.setEnabled(False)
        elif name in self.existing:
            self.error_label.setText(f"分支 '{name}' 已存在")
            self.ok_btn.setEnabled(False)
        else:
            self.error_label.setText("")
            self.ok_btn.setEnabled(True)


class GitInstallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安装 Git")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("未检测到 Git 环境，是否安装？"))

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.install_btn = QPushButton("一键安装 Git")
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self._start_install)
        btn_layout.addWidget(self.install_btn)

        layout.addLayout(btn_layout)

    def show_progress(self, text: str):
        self.install_btn.hide()
        self.progress.show()
        self.status_label.setText(text)


def confirm_discard(parent, msg="确定要丢弃未保存的变更吗？") -> bool:
    result = QMessageBox.question(
        parent, "未提交变更", msg,
        QMessageBox.Discard | QMessageBox.Cancel,
        QMessageBox.Cancel,
    )
    return result == QMessageBox.Discard


def unsaved_changes_dialog(parent) -> str:
    box = QMessageBox(parent)
    box.setWindowTitle("未提交变更")
    box.setText("右侧编辑区存在未提交的修改，请选择操作：")
    box.setIcon(QMessageBox.Warning)

    commit_btn = box.addButton("提交变更", QMessageBox.AcceptRole)
    discard_btn = box.addButton("丢弃变更", QMessageBox.DestructiveRole)
    cancel_btn = box.addButton("取消当前操作", QMessageBox.RejectRole)
    box.setDefaultButton(cancel_btn)
    box.exec_()

    clicked = box.clickedButton()
    if clicked == commit_btn:
        return "commit"
    elif clicked == discard_btn:
        return "discard"
    return "cancel"


def show_info(parent, title, text):
    QMessageBox.information(parent, title, text)


def show_error(parent, title, text):
    QMessageBox.warning(parent, title, text)
