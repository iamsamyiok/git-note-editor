import os
import sys
import html
import datetime
import json
import logging

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QAction, QFileDialog,
    QStatusBar, QMessageBox, QApplication,
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QShortcut, QTabWidget,
)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt, QRectF, QTimer, QEvent, QSize


logger = logging.getLogger(__name__)

from version_manager import VersionManager, BRANCH_COLORS
from graph_widget import GraphView
from editor_widget import EditorWidget
from dialogs import (
    CommitDialog, BranchDialog,
    unsaved_changes_dialog, show_info, show_error,
)
from screenshot_widget import ScreenshotWidget
from settings_dialog import SettingsDialog
from bookmark_widget import BookmarkWidget
from chat_widget import ChatWidget
from cloudcode_executor import CloudCodeExecutor, TaskStatus
from cloudcode_dialog import CloudCodeTaskDialog
from reminder_widget import ReminderWidget
from path_helper import resource_path, get_data_file_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.vm = VersionManager()

        self.setWindowTitle("版本化富文本笔记")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 850)

        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.note_widget = QWidget()
        note_layout = QVBoxLayout(self.note_widget)
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        note_layout.addWidget(self.splitter)

        self.graph_view = GraphView()
        self.editor = EditorWidget()
        self.splitter.addWidget(self.graph_view)
        self.splitter.addWidget(self.editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.bookmark_widget = BookmarkWidget()
        self.chat_widget = ChatWidget()
        self.reminder_widget = ReminderWidget()
        self.chat_widget.export_requested.connect(self._on_chat_export)
        self.reminder_widget.status_update.connect(self._update_status)
        
        self.tab_widget.addTab(self.note_widget, "📝 笔记")
        self.tab_widget.addTab(self.bookmark_widget, "🔗 网址收藏")
        self.tab_widget.addTab(self.chat_widget, "💬 AI聊天")
        self.tab_widget.addTab(self.reminder_widget, "⏰ 提醒")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 — 请新建或打开一个笔记文件")

        self.graph_view.node_clicked.connect(self._on_node_clicked)
        self.graph_view.delete_requested.connect(self._on_delete_requested)
        self.graph_view.graph_refresh_requested.connect(self._refresh_graph)
        self.graph_view.new_commit_requested.connect(self._on_commit)
        self.graph_view.new_branch_requested.connect(self._on_new_branch)
        self.graph_view.new_branch_at_requested.connect(self._on_new_branch_at)
        self.graph_view.switch_branch_requested.connect(self._on_switch_branch)
        self.editor.new_file_requested.connect(self._on_new_file)
        self.editor.open_file_requested.connect(self._on_open_file)
        self.editor.export_requested.connect(self._on_export)
        self.editor.content_changed.connect(self._on_editor_changed)
        self.editor.settings_requested.connect(self._on_open_settings)
        self.editor.status_update.connect(self._update_status)


        self.chat_widget.status_update.connect(self._update_status)

        self.screenshot_widget = ScreenshotWidget()
        self.screenshot_widget.screenshot_taken.connect(self._on_screenshot_taken)

        self._setup_shortcuts()
        self._start_global_hotkey()
        self.window_geometry = self.geometry()
        self.window_state = self.windowState()

        self.reminder_widget.start_scheduler()
        self._setup_auto_save_timer()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_open_file)
        QShortcut(QKeySequence("Ctrl+N"), self, self._on_new_file)
        QShortcut(QKeySequence("Ctrl+M"), self, self._on_commit)
        QShortcut(QKeySequence("Ctrl+B"), self, self._on_new_branch)
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self._on_export("pdf"))
        QShortcut(QKeySequence("Ctrl+Shift+C"), self._switch_to_chat)

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

    def _on_new_branch_at(self, hash_value: str):
        if not self.vm.repo_ok():
            return

        branches = self.vm.branches()
        dlg = BranchDialog(branches, self)
        if dlg.exec_() != BranchDialog.Accepted:
            return

        ok, err = self.vm.create_branch(dlg.branch_name(), hash_value)
        if not ok:
            show_error(self, "创建分支失败", err)
            return

        self._refresh_graph()
        self.status_bar.showMessage(
            f"已在 {hash_value[:8]} 处创建分支：{dlg.branch_name()}"
        )

    def _on_switch_branch(self, branch_name: str):
        if not self.vm.repo_ok():
            return

        if self.editor.is_modified():
            result = unsaved_changes_dialog(self)
            if result == "cancel":
                return
            elif result == "commit":
                self._on_commit()
                if self.editor.is_modified():
                    return

        ok, err = self.vm.switch_branch(branch_name)
        if not ok:
            show_error(self, "切换分支失败", err)
            return

        html = self.vm.read_html()
        self.editor.set_html(html)
        self.editor.set_modified(False)
        self._refresh_graph()
        self.status_bar.showMessage(f"已切换到分支：{branch_name}")

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
        if self.editor.is_modified():
            title = self.windowTitle()
            if not title.startswith("*"):
                self.setWindowTitle("*" + title)
        else:
            title = self.windowTitle()
            if title.startswith("*"):
                self.setWindowTitle(title[1:])

    def _on_export(self, fmt: str):
        if not self.vm.repo_ok():
            return

        ext_map = {
            "pdf": "PDF 文件 (*.pdf)",
            "html": "HTML 文件 (*.html)",
            "png": "PNG 文件 (*.png)",
            "svg": "SVG 文件 (*.svg)",
        }
        fmt_ext = {
            "pdf": ".pdf",
            "html": ".html",
            "png": ".png",
            "svg": ".svg",
        }

        base = os.path.basename(self.vm.root_path)
        path, _ = QFileDialog.getSaveFileName(
            self, f"导出为 {fmt.upper()}",
            base + fmt_ext[fmt],
            ext_map[fmt],
        )
        if not path:
            return

        try:
            if fmt == "pdf":
                self._export_pdf(path)
            elif fmt == "html":
                self._export_html(path)
            elif fmt == "png":
                self._export_png(path)
            elif fmt == "svg":
                self._export_svg(path)
            self.status_bar.showMessage(f"已导出：{path}")
        except Exception as e:
            show_error(self, "导出失败", str(e))

    def _export_pdf(self, path: str):
        from PyQt5.QtPrintSupport import QPrinter
        from PyQt5.QtGui import QTextDocument

        doc = QTextDocument()
        doc.setHtml(self.editor.to_html())
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSizeMm(QPrinter.A4)
        doc.print_(printer)

    def _export_html(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.to_html())

    def _export_png(self, path: str):
        from PyQt5.QtGui import QImage, QPainter, QTextDocument

        qte = self.editor.editor
        doc = QTextDocument()
        doc.setHtml(self.editor.to_html())

        page_width = qte.viewport().width()
        page_size = qte.viewport().size()
        doc.setPageSize(page_size)

        content_height = int(doc.size().height()) + 20
        content_width = page_width

        image = QImage(content_width, content_height, QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        doc.drawContents(painter)
        painter.end()

        image.save(path, "PNG")

    def _export_svg(self, path: str):
        from PyQt5.QtSvg import QSvgGenerator
        from PyQt5.QtGui import QPainter as QPt, QTextDocument

        qte = self.editor.editor
        doc = QTextDocument()
        doc.setHtml(self.editor.to_html())

        page_width = qte.viewport().width()
        page_size = qte.viewport().size()
        doc.setPageSize(page_size)

        content_height = int(doc.size().height()) + 20
        content_width = page_width

        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(content_width, content_height))
        generator.setViewBox(QRectF(0, 0, content_width, content_height))

        painter = QPt(generator)
        doc.drawContents(painter)
        painter.end()

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
        self.graph_view.update_branches(self.vm.branches(), self.vm.current_branch())

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

    def _start_global_hotkey(self):
        try:
            from pynput import keyboard
        except Exception as e:
            logger.warning("pynput 导入失败，全局热键将不可用: %s", e)
            self.hotkey = None
            return

        try:
            def on_activate():
                QApplication.instance().postEvent(
                    self, ScreenshotEvent()
                )

            self.hotkey = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+s': on_activate
            })
            self.hotkey.start()
        except Exception as e:
            logger.warning("全局热键启动失败，截图快捷键将不可用: %s", e)
            self.hotkey = None

    def _setup_auto_save_timer(self):
        """启动定时自动保存（每 60 秒），仅写 html 文件，不创建 commit。"""
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(60 * 1000)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start()

    def _auto_save(self):
        """自动保存：如果编辑器有修改，则写入 html 文件，但不创建 commit。"""
        try:
            if not self.vm.repo_ok():
                return
            if not self.editor.is_modified():
                return
            self.vm.write_html(self.editor.to_html())
            self.status_bar.showMessage("已自动保存", 3000)
        except Exception as e:
            logger.exception("自动保存失败: %s", e)

    def customEvent(self, event):
        if isinstance(event, ScreenshotEvent):
            self._trigger_screenshot()

    def _trigger_screenshot(self):
        self.window_geometry = self.geometry()
        self.window_state = self.windowState()
        self.hide()
        QTimer.singleShot(100, self._show_screenshot_widget)

    def _show_screenshot_widget(self):
        if self.screenshot_widget:
            screen = QApplication.primaryScreen()
            self.screenshot_widget.setGeometry(
                screen.geometry()
            )
            self.screenshot_widget.show()
            self.screenshot_widget.setFocus()

    def _on_screenshot_taken(self, filepath):
        if not filepath or not os.path.exists(filepath):
            self.setGeometry(self.window_geometry)
            self.setWindowState(self.window_state)
            self.show()
            self.raise_()
            self.activateWindow()
            return

        img_src = filepath
        if self.vm.repo_ok() and self.vm.imgs_dir:
            import shutil
            filename = os.path.basename(filepath)
            dst = os.path.join(self.vm.imgs_dir, filename)
            shutil.copy2(filepath, dst)
            img_src = os.path.join("imgs", filename).replace("\\", "/")

        # 对图片路径进行 HTML 转义，防止路径中包含特殊字符导致 XSS
        safe_src = html.escape(img_src, quote=True)
        screenshot_html = f'''
        <div style="display:block; margin: 10px 0;">
            <img src="{safe_src}" width="100%">
        </div>
        <br>
        '''
        cursor = self.editor.editor.textCursor()
        cursor.insertHtml(screenshot_html)

        self.setGeometry(self.window_geometry)
        self.setWindowState(self.window_state)
        self.show()
        self.raise_()
        self.activateWindow()

    def _update_status(self, message: str):
        self.status_bar.showMessage(message, 10000)

    def _on_open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == SettingsDialog.Accepted:
            config = dialog.get_config()

            config_path = get_data_file_path("config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.status_bar.showMessage("设置已保存", 3000)

    def closeEvent(self, event):
        # 关闭前自动保存一次（仅写文件，不创建 commit）
        self._auto_save()

        # 停止全局热键（容错处理）
        hotkey = getattr(self, 'hotkey', None)
        if hotkey is not None:
            try:
                hotkey.stop()
            except Exception as e:
                logger.warning("停止全局热键失败: %s", e)

        if not self._check_dirty():
            event.ignore()
        else:
            event.accept()


class ScreenshotEvent(QEvent):
    TYPE = QEvent.User + 1
    
    def __init__(self):
        super().__init__(self.TYPE)


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
