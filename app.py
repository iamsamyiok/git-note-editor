import os
import sys

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QMenuBar, QAction, QFileDialog,
    QStatusBar, QMessageBox, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal

from git_manager import GitManager
from git_installer import check_git, install_git
from graph_widget import GraphView
from editor_widget import EditorWidget
from dialogs import (
    CommitDialog, BranchDialog, GitInstallDialog,
    unsaved_changes_dialog, confirm_discard, show_info, show_error,
)

BRANCH_COLORS = [
    "#2196F3", "#FF5722", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#795548", "#607D8B",
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.git = GitManager()
        self.current_hash = ""
        self.ignore_editor_change = False

        ok, msg = check_git()
        if not ok:
            self._handle_no_git()
            return

        self.setWindowTitle("Git 版本化富文本笔记工具")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 850)

        self._setup_menu()

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
        self.graph_view.node_right_clicked.connect(self._on_node_context_menu)
        self.graph_view.graph_refresh_requested.connect(self._refresh_graph)
        self.editor.content_changed.connect(self._on_editor_changed)

    def _setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("文件(&F)")

        new_action = QAction("新建文件(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_file)
        file_menu.addAction(new_action)

        open_action = QAction("打开文件(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        self.commit_action = QAction("Commit 提交(&C)", self)
        self.commit_action.setShortcut("Ctrl+Return")
        self.commit_action.triggered.connect(self._on_commit)
        self.commit_action.setEnabled(False)
        file_menu.addAction(self.commit_action)

        self.branch_action = QAction("新建分支(&B)", self)
        self.branch_action.setShortcut("Ctrl+B")
        self.branch_action.triggered.connect(self._on_new_branch)
        self.branch_action.setEnabled(False)
        file_menu.addAction(self.branch_action)

    def _handle_no_git(self):
        dlg = GitInstallDialog(self)
        if dlg.exec_() == GitInstallDialog.Accepted:
            dlg.show_progress("正在从清华镜像下载 Git...")
            QApplication.processEvents()
            ok = install_git(self)
            if ok:
                dlg.status_label.setText("安装完成！")
                show_info(self, "安装成功", "Git 已安装，请重启程序。")
            else:
                show_error(self, "安装失败", "Git 安装失败，请手动安装。")
        self.close()

    # ---------- file operations ----------

    def _on_new_file(self):
        if not self._check_dirty():
            return

        folder = QFileDialog.getExistingDirectory(self, "选择笔记存放目录")
        if not folder:
            return

        name, ok = QFileDialog.getSaveFileName(
            self, "笔记文件名", folder, "HTML Files (*.html)"
        )
        if not ok or not name:
            return

        if self.git.init_repo(os.path.dirname(name), os.path.basename(name)):
            self.editor.imgs_dir = self.git.imgs_dir
            self.editor.set_html("<html><body></body></html>")
            self.editor.set_modified(False)
            self.commit_action.setEnabled(True)
            self.branch_action.setEnabled(True)
            self._refresh_graph()
            self.status_bar.showMessage(f"已创建：{name}")
            self.setWindowTitle(f"Git 版本化富文本笔记工具 — {os.path.basename(name)}")

    def _on_open_file(self):
        if not self._check_dirty():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开笔记文件", "", "HTML Files (*.html)"
        )
        if not path:
            return

        ok, err = self.git.open_repo(path)
        if not ok:
            show_error(self, "打开失败", err)
            return

        self.editor.imgs_dir = self.git.imgs_dir

        html = self.git.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)

        self.commit_action.setEnabled(True)
        self.branch_action.setEnabled(True)

        self._refresh_graph()

        self.status_bar.showMessage(f"已打开：{path}")
        self.setWindowTitle(f"Git 版本化富文本笔记工具 — {os.path.basename(path)}")

    # ---------- commit & branch ----------

    def _on_commit(self):
        if not self.git.repo_ok():
            return

        dlg = CommitDialog(self)
        if dlg.exec_() != CommitDialog.Accepted:
            return

        self.git.write_html(self.editor.to_html())
        ok, err = self.git.commit(dlg.commit_message())
        if not ok:
            show_error(self, "提交失败", err)
            return

        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage("提交成功")

    def _on_new_branch(self):
        if not self.git.repo_ok():
            return

        if not self.current_hash:
            show_info(self, "提示", "请先在左侧图谱中选中一个节点作为分支起点。")
            return

        branches = self.git._branches()
        dlg = BranchDialog(branches, self)
        if dlg.exec_() != BranchDialog.Accepted:
            return

        ok, err = self.git.create_branch(
            dlg.branch_name(), self.current_hash
        )
        if not ok:
            show_error(self, "创建分支失败", err)
            return

        ok2, err2 = self.git.switch_branch(dlg.branch_name())
        if not ok2:
            show_error(self, "切换分支失败", err2)
            return

        html = self.git.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage(f"已切换到分支：{dlg.branch_name()}")

    # ---------- node interaction ----------

    def _on_node_clicked(self, hash_value: str):
        if not self.git.repo_ok():
            return

        if hash_value == self.current_hash:
            return

        if self.editor.is_modified():
            result = unsaved_changes_dialog(self)
            if result == "cancel":
                self.graph_view.select_node(self.current_hash)
                return
            elif result == "commit":
                self._on_commit()
                if self.editor.is_modified():
                    self.graph_view.select_node(self.current_hash)
                    return
            elif result == "discard":
                pass

        ok, err = self.git.checkout_commit(hash_value)
        if not ok:
            show_error(self, "切换失败", err)
            self.graph_view.select_node(self.current_hash)
            return

        self.current_hash = hash_value
        html = self.git.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self.status_bar.showMessage(f"已切换到：{hash_value[:8]}")

    def _on_node_context_menu(self, hash_value: str, _pos):
        if not self.git.repo_ok():
            return

        if self.git.is_root(hash_value):
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

        ok, err = self.git.delete_commit(hash_value)
        if not ok:
            show_error(self, "删除失败", err)
            return

        self.current_hash = self.git.current_hash()
        html = self.git.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage("提交已删除，图谱已更新")

    # ---------- editor ----------

    def _on_editor_changed(self):
        if self.ignore_editor_change:
            return

    # ---------- graph ----------

    def _refresh_graph(self):
        if not self.git.repo_ok():
            return

        commits = self.git.all_commits()
        self.current_hash = self.git.current_hash()

        color_idx = 0
        branch_color_map = {}
        for h, c in commits.items():
            if c.branch_name and c.branch_name not in branch_color_map:
                branch_color_map[c.branch_name] = BRANCH_COLORS[
                    color_idx % len(BRANCH_COLORS)
                ]
                color_idx += 1
            c.branch_color = branch_color_map.get(c.branch_name, "#9E9E9E")

        root_hash = None
        for h, c in commits.items():
            if not c.parent_hashes:
                c.is_root = True
                root_hash = h
                break

        self.graph_view.set_commits(commits, self.current_hash)

    # ---------- helpers ----------

    def _check_dirty(self) -> bool:
        if not self.git.repo_ok():
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
