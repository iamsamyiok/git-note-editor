import os
import sys

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QAction, QFileDialog,
    QStatusBar, QMessageBox, QApplication, QToolBar,
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from version_manager import VersionManager, BRANCH_COLORS
from graph_widget import GraphView
from editor_widget import EditorWidget
from dialogs import (
    CommitDialog, BranchDialog,
    unsaved_changes_dialog, show_info, show_error,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.vm = VersionManager()

        self.setWindowTitle("版本化富文本笔记")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 850)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._setup_toolbar()

        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        self.graph_view = GraphView()
        self.editor = EditorWidget()
        self.splitter.addWidget(self.graph_view)
        self.splitter.addWidget(self.editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 — 请新建或打开一个笔记文件")

        self.graph_view.node_clicked.connect(self._on_node_clicked)
        self.graph_view.delete_requested.connect(self._on_delete_requested)
        self.graph_view.graph_refresh_requested.connect(self._refresh_graph)
        self.editor.content_changed.connect(self._on_editor_changed)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        new_action = QAction(icon, "新建笔记", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_file)
        toolbar.addAction(new_action)

        open_action = QAction("打开笔记", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        self.commit_action = QAction("提交变更", self)
        self.commit_action.setShortcut("Ctrl+Return")
        self.commit_action.triggered.connect(self._on_commit)
        self.commit_action.setEnabled(False)
        toolbar.addAction(self.commit_action)

        self.branch_action = QAction("新建分支", self)
        self.branch_action.setShortcut("Ctrl+B")
        self.branch_action.triggered.connect(self._on_new_branch)
        self.branch_action.setEnabled(False)
        toolbar.addAction(self.branch_action)

    def _on_new_file(self):
        if not self._check_dirty():
            return

        folder = QFileDialog.getExistingDirectory(self, "选择笔记存放目录")
        if not folder:
            return

        name, ok = QFileDialog.getSaveFileName(
            self, "笔记文件名", folder, "HTML 文件 (*.html)"
        )
        if not ok or not name:
            return

        if self.vm.init_repo(os.path.dirname(name), os.path.basename(name)):
            self.editor.imgs_dir = self.vm.imgs_dir
            self.editor.set_html("<html><body></body></html>")
            self.editor.set_modified(False)
            self.commit_action.setEnabled(True)
            self.branch_action.setEnabled(True)
            self._refresh_graph()
            self.status_bar.showMessage(f"已创建：{name}")
            self.setWindowTitle(f"版本化富文本笔记 — {os.path.basename(name)}")

    def _on_open_file(self):
        if not self._check_dirty():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开笔记文件", "", "HTML 文件 (*.html)"
        )
        if not path:
            return

        ok, err = self.vm.open_repo(path)
        if not ok:
            show_error(self, "打开失败", err)
            return

        self.editor.imgs_dir = self.vm.imgs_dir

        html = self.vm.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)

        self.commit_action.setEnabled(True)
        self.branch_action.setEnabled(True)

        self._refresh_graph()

        self.status_bar.showMessage(f"已打开：{path}")
        self.setWindowTitle(f"版本化富文本笔记 — {os.path.basename(path)}")

    def _on_commit(self):
        if not self.vm.repo_ok():
            return

        dlg = CommitDialog(self)
        if dlg.exec_() != CommitDialog.Accepted:
            return

        self.vm.write_html(self.editor.to_html())
        ok, err = self.vm.commit(dlg.commit_message())
        if not ok:
            show_error(self, "提交失败", err)
            return

        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage("提交成功")

    def _on_new_branch(self):
        if not self.vm.repo_ok():
            return

        if not self.vm.current_commit:
            show_info(self, "提示", "请先在左侧图谱中选中一个节点作为分支起点。")
            return

        branches = self.vm.branches()
        dlg = BranchDialog(branches, self)
        if dlg.exec_() != BranchDialog.Accepted:
            return

        from_commit = self.vm.current_commit
        ok, err = self.vm.create_branch(dlg.branch_name(), from_commit)
        if not ok:
            show_error(self, "创建分支失败", err)
            return

        html = self.vm.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage(f"已创建并切换到分支：{dlg.branch_name()}")

    def _on_node_clicked(self, hash_value: str):
        if not self.vm.repo_ok():
            return

        if hash_value == self.vm.current_commit:
            return

        if self.editor.is_modified():
            result = unsaved_changes_dialog(self)
            if result == "cancel":
                self.graph_view.select_node(self.vm.current_commit)
                return
            elif result == "commit":
                self._on_commit()
                if self.editor.is_modified():
                    self.graph_view.select_node(self.vm.current_commit)
                    return
            elif result == "discard":
                pass

        ok, err = self.vm.checkout_commit(hash_value)
        if not ok:
            show_error(self, "切换失败", err)
            self.graph_view.select_node(self.vm.current_commit)
            return

        html = self.vm.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self.status_bar.showMessage(f"已切换到：{hash_value[:8]}")

    def _on_delete_requested(self, hash_value: str):
        if not self.vm.repo_ok():
            return

        if self.vm.is_root(hash_value):
            QMessageBox.information(self, "提示", "根节点不可删除。")
            return

        result = QMessageBox.question(
            self, "删除提交",
            "确定要删除此提交吗？删除后无法恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        ok, err = self.vm.delete_commit(hash_value)
        if not ok:
            show_error(self, "删除失败", err)
            return

        html = self.vm.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage("提交已删除，图谱已更新")

    def _on_editor_changed(self):
        pass

    def _refresh_graph(self):
        if not self.vm.repo_ok():
            return

        commits = self.vm.all_commits()
        cur = self.vm.current_hash()

        color_idx = 0
        branch_color_map = {}
        for h, c in commits.items():
            if c.branch_name and c.branch_name not in branch_color_map:
                branch_color_map[c.branch_name] = BRANCH_COLORS[
                    color_idx % len(BRANCH_COLORS)
                ]
                color_idx += 1
            c.branch_color = branch_color_map.get(c.branch_name, "#9E9E9E")

        self.graph_view.set_commits(commits, cur)

    def _check_dirty(self) -> bool:
        if not self.vm.repo_ok():
            return True
        if not self.editor.is_modified():
            return True

        result = unsaved_changes_dialog(self)
        if result == "cancel":
            return False
        elif result == "commit":
            self._on_commit()
            return not self.editor.is_modified()
        return True

    def closeEvent(self, event):
        if not self._check_dirty():
            event.ignore()
        else:
            event.accept()


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
