import os
import html
import uuid
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction,
    QTextEdit, QFileDialog, QColorDialog, QInputDialog,
    QComboBox, QPushButton, QLabel, QMessageBox, QMenu,
    QDialog, QLineEdit, QCheckBox, QShortcut,
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QTextListFormat, QImage,
    QTextCursor, QPainter, QPixmap, QMouseEvent, QCursor,
    QKeySequence, QDragEnterEvent, QDropEvent, QTextDocument,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPoint, QEvent
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QApplication

from cloudcode_dialog import CloudCodeTaskDialog
from cloudcode_result import CloudCodeResultDialog
from cloudcode_executor import CloudCodeExecutor, TaskStatus
from path_helper import get_data_file_path


logger = logging.getLogger(__name__)


class FormatPainterTextEdit(QTextEdit):
    # 粘贴或拖入图片时触发，参数为 QImage 或本地文件路径(str)
    image_insert_requested = pyqtSignal(object)

    SUPPORTED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.format_painter_active = False
        self.format_painter_format = None
        self.setAcceptDrops(True)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.format_painter_active and self.format_painter_format:
            cursor = self.textCursor()
            cursor.mergeCharFormat(self.format_painter_format)
            self.format_painter_active = False
            self.format_painter_format = None
            self.viewport().setCursor(Qt.IBeamCursor)
        super().mouseReleaseEvent(event)

    def canInsertFromMimeData(self, source):
        # 允许粘贴剪贴板中的图片
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.image_insert_requested.emit(img)
                return
        super().insertFromMimeData(source)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = os.path.splitext(url.toLocalFile())[1].lower()
                    if ext in self.SUPPORTED_IMAGE_EXTS:
                        event.acceptProposedAction()
                        return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = os.path.splitext(url.toLocalFile())[1].lower()
                    if ext in self.SUPPORTED_IMAGE_EXTS:
                        event.acceptProposedAction()
                        return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            handled = False
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = os.path.splitext(path)[1].lower()
                    if ext in self.SUPPORTED_IMAGE_EXTS:
                        self.image_insert_requested.emit(path)
                        handled = True
            if handled:
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class FindReplaceDialog(QDialog):
    """查找替换对话框，支持大小写敏感、整词匹配与高亮。"""

    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("查找替换")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("查找："))
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("输入要查找的内容")
        self.find_edit.returnPressed.connect(self.find_next)
        find_row.addWidget(self.find_edit, 1)
        layout.addLayout(find_row)

        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("替换："))
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("输入替换内容")
        replace_row.addWidget(self.replace_edit, 1)
        layout.addLayout(replace_row)

        option_row = QHBoxLayout()
        self.case_check = QCheckBox("区分大小写")
        self.word_check = QCheckBox("整词匹配")
        option_row.addWidget(self.case_check)
        option_row.addWidget(self.word_check)
        option_row.addStretch()
        layout.addLayout(option_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        find_next_btn = QPushButton("查找下一个")
        find_prev_btn = QPushButton("查找上一个")
        replace_btn = QPushButton("替换")
        replace_all_btn = QPushButton("全部替换")
        close_btn = QPushButton("关闭")
        find_next_btn.clicked.connect(self.find_next)
        find_prev_btn.clicked.connect(self.find_prev)
        replace_btn.clicked.connect(self.replace_one)
        replace_all_btn.clicked.connect(self.replace_all)
        close_btn.clicked.connect(self.close)
        for b in (find_next_btn, find_prev_btn, replace_btn, replace_all_btn):
            btn_row.addWidget(b)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

    def _flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.case_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.word_check.isChecked():
            flags |= QTextDocument.FindWholeWords
        return flags

    def find_next(self):
        text = self.find_edit.text()
        if not text:
            return
        cursor = self.editor.textCursor()
        found = self.editor.find(text, cursor, self._flags())
        if found:
            self.status_label.setText("已匹配")
        else:
            # 回绕到文档开头继续查找
            cursor.movePosition(QTextCursor.Start)
            if self.editor.find(text, cursor, self._flags()):
                self.status_label.setText("已从开头重新匹配")
            else:
                self.status_label.setText("未找到")

    def find_prev(self):
        text = self.find_edit.text()
        if not text:
            return
        flags = self._flags() | QTextDocument.FindBackward
        cursor = self.editor.textCursor()
        found = self.editor.find(text, cursor, flags)
        if found:
            self.status_label.setText("已匹配")
        else:
            cursor.movePosition(QTextCursor.End)
            if self.editor.find(text, cursor, flags):
                self.status_label.setText("已从末尾重新匹配")
            else:
                self.status_label.setText("未找到")

    def replace_one(self):
        text = self.find_edit.text()
        if not text:
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == text:
            cursor.insertText(self.replace_edit.text())
        self.find_next()

    def replace_all(self):
        text = self.find_edit.text()
        if not text:
            return
        replace_text = self.replace_edit.text()
        flags = self._flags()
        doc = self.editor.document()
        root_cursor = self.editor.textCursor()
        root_cursor.beginEditBlock()
        root_cursor.movePosition(QTextCursor.Start)
        search_cursor = QTextCursor(doc)
        search_cursor.movePosition(QTextCursor.Start)
        count = 0
        while True:
            found = doc.find(text, search_cursor, flags)
            if found.isNull():
                break
            found.insertText(replace_text)
            # 从替换后的位置继续，避免替换文本包含原文本时死循环
            search_cursor.setPosition(found.selectionEnd())
            count += 1
        root_cursor.endEditBlock()
        self.status_label.setText(f"已替换 {count} 处")


class EditorWidget(QWidget):
    content_changed = pyqtSignal()
    new_file_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    export_requested = pyqtSignal(str)
    settings_requested = pyqtSignal()
    status_update = pyqtSignal(str)

    def __init__(self, imgs_dir=""):
        super().__init__()
        self.imgs_dir = imgs_dir
        self.cloudcode_executor = CloudCodeExecutor()
        # 跟踪进行中的 OCR 线程，避免被垃圾回收
        self._ocr_threads = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 4, 4, 2)

        new_btn = QPushButton("新建笔记")
        new_btn.setFixedHeight(28)
        new_btn.clicked.connect(self._emit_new_file)
        top_bar.addWidget(new_btn)

        open_btn = QPushButton("打开笔记")
        open_btn.setFixedHeight(28)
        open_btn.clicked.connect(self._emit_open_file)
        top_bar.addWidget(open_btn)

        export_btn = QPushButton("导出")
        export_btn.setFixedHeight(28)
        export_btn.clicked.connect(self._on_export)
        top_bar.addWidget(export_btn)

        cloudcode_btn = QPushButton("🤖 Cloud Code")
        cloudcode_btn.setFixedHeight(28)
        cloudcode_btn.clicked.connect(self._open_cloudcode_task)
        cloudcode_btn.setStyleSheet("""
            QPushButton {
                background: #6610f2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #520dc2;
            }
        """)
        top_bar.addWidget(cloudcode_btn)

        top_bar.addStretch()

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(self.toolbar.iconSize())
        self._setup_format_toolbar()
        top_bar.addWidget(self.toolbar)

        layout.addLayout(top_bar)

        self.editor = FormatPainterTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.textChanged.connect(self.content_changed.emit)
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._on_editor_context_menu)
        self.editor.image_insert_requested.connect(self._on_image_insert_requested)
        layout.addWidget(self.editor)

        # Ctrl+F 查找替换
        self._find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._find_shortcut.activated.connect(self._show_find_replace)
        self._find_replace_dialog = None

    def _setup_format_toolbar(self):
        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.setFixedWidth(60)
        for sz in ["9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36", "48"]:
            self.font_combo.addItem(sz)
        self.font_combo.setCurrentText("14")
        self.font_combo.currentTextChanged.connect(self._on_font_size)
        self.toolbar.addWidget(QLabel("字号"))
        self.toolbar.addWidget(self.font_combo)
        self.toolbar.addSeparator()

        headings = [
            ("正文", 0),
            ("一级标题", 1),
            ("二级标题", 2),
            ("三级标题", 3),
            ("四级标题", 4),
        ]
        for label, level in headings:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _, l=level: self._set_heading(l))
            self.toolbar.addWidget(btn)
        self.toolbar.addSeparator()

        actions = [
            ("bold", "B", True, "加粗"),
            ("italic", "I", True, "斜体"),
            ("underline", "U", True, "下划线"),
            (None, None, False, ""),
            ("color", "A色", False, "文字颜色"),
            ("bgcolor", "底色", False, "背景色"),
            (None, None, False, ""),
            ("left", "左", False, "左对齐"),
            ("center", "中", False, "居中"),
            ("right", "右", False, "右对齐"),
            ("justify", "两端", False, "两端对齐"),
            (None, None, False, ""),
            ("ulist", "无序", False, "无序列表"),
            ("olist", "有序", False, "有序列表"),
            (None, None, False, ""),
            ("table", "表格", False, "插入表格"),
            ("link", "链接", False, "超链接"),
            ("image", "图片", False, "插入图片"),
            (None, None, False, ""),
            ("format_painter", "格式刷", False, "格式刷"),
        ]

        for action_id, label, checkable, tip in actions:
            if action_id is None:
                self.toolbar.addSeparator()
                continue
            act = QAction(label, self)
            act.setToolTip(tip)
            act.triggered.connect(lambda _, a=action_id: self._on_format_action(a))
            self.toolbar.addAction(act)

    def _emit_new_file(self):
        self.new_file_requested.emit()

    def _emit_open_file(self):
        self.open_file_requested.emit()

    def _on_font_size(self, text):
        try:
            size = int(text)
        except ValueError:
            return
        cf = QTextCharFormat()
        cf.setFontPointSize(size)
        self.editor.mergeCurrentCharFormat(cf)
        self.editor.setFocus()

    def _set_heading(self, level: int):
        cursor = self.editor.textCursor()
        cf = QTextCharFormat()
        if level == 0:
            cf.setFontPointSize(14)
            cf.setFontWeight(QFont.Normal)
        elif level == 1:
            cf.setFontPointSize(28)
            cf.setFontWeight(QFont.Bold)
        elif level == 2:
            cf.setFontPointSize(22)
            cf.setFontWeight(QFont.Bold)
        elif level == 3:
            cf.setFontPointSize(18)
            cf.setFontWeight(QFont.Bold)
        elif level == 4:
            cf.setFontPointSize(15)
            cf.setFontWeight(QFont.Bold)
        cursor.mergeCharFormat(cf)
        self.editor.setFocus()

    def _on_format_action(self, action: str):
        cursor = self.editor.textCursor()

        if action == "bold":
            cf = QTextCharFormat()
            is_bold = self.editor.fontWeight() != QFont.Bold
            cf.setFontWeight(QFont.Bold if is_bold else QFont.Normal)
            cursor.mergeCharFormat(cf)
        elif action == "italic":
            cf = QTextCharFormat()
            cf.setFontItalic(not self.editor.fontItalic())
            cursor.mergeCharFormat(cf)
        elif action == "underline":
            cf = QTextCharFormat()
            cf.setFontUnderline(not self.editor.fontUnderline())
            cursor.mergeCharFormat(cf)
        elif action == "color":
            color = QColorDialog.getColor(parent=self)
            if color.isValid():
                cf = QTextCharFormat()
                cf.setForeground(color)
                cursor.mergeCharFormat(cf)
        elif action == "bgcolor":
            color = QColorDialog.getColor(parent=self)
            if color.isValid():
                cf = QTextCharFormat()
                cf.setBackground(color)
                cursor.mergeCharFormat(cf)
        elif action == "left":
            self.editor.setAlignment(Qt.AlignLeft)
        elif action == "center":
            self.editor.setAlignment(Qt.AlignCenter)
        elif action == "right":
            self.editor.setAlignment(Qt.AlignRight)
        elif action == "justify":
            self.editor.setAlignment(Qt.AlignJustify)
        elif action == "ulist":
            lf = QTextListFormat()
            lf.setStyle(QTextListFormat.ListDisc)
            cursor.createList(lf)
        elif action == "olist":
            lf = QTextListFormat()
            lf.setStyle(QTextListFormat.ListDecimal)
            cursor.createList(lf)
        elif action == "table":
            self._insert_table()
        elif action == "link":
            self._insert_link(cursor)
        elif action == "image":
            self._insert_image()
        elif action == "format_painter":
            self._format_painter()
        self.editor.setFocus()

    def _format_painter(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.editor.format_painter_format = cursor.charFormat()
            self.editor.format_painter_active = True
            self.editor.viewport().setCursor(Qt.CrossCursor)

    def _insert_table(self):
        rows, ok1 = QInputDialog.getInt(self, "插入表格", "行数：", 3, 1, 20, 1)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "插入表格", "列数：", 3, 1, 10, 1)
        if not ok2:
            return
        table_html = '<table border="1" cellspacing="0" cellpadding="4">'
        for _ in range(rows):
            table_html += "<tr>"
            for _ in range(cols):
                table_html += "<td>&nbsp;</td>"
            table_html += "</tr>"
        table_html += "</table>"
        self.editor.textCursor().insertHtml(table_html)

    def _insert_link(self, cursor):
        """插入超链接，对 URL 进行协议校验与 HTML 转义，防止 XSS。"""
        url = QInputDialog.getText(self, "插入超链接", "URL:")
        if not (url[1] and url[0]):
            return
        raw_url = url[0].strip()
        # URL 协议校验：只允许 http:// 和 https://
        lower = raw_url.lower()
        if not (lower.startswith("http://") or lower.startswith("https://")):
            QMessageBox.warning(
                self, "提示",
                "仅支持 http:// 或 https:// 协议的超链接，已阻止插入。"
            )
            return
        safe_url = html.escape(raw_url, quote=True)
        cursor.insertHtml(f'<a href="{safe_url}">{safe_url}</a>')

    def _insert_image(self):
        if not self.imgs_dir:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if not path:
            return

        self._insert_image_from_path(path)

    def _on_image_insert_requested(self, image_data):
        """处理粘贴或拖入的图片。image_data 可为 QImage 或本地文件路径(str)。"""
        if not self.imgs_dir:
            QMessageBox.warning(
                self, "提示",
                "请先新建或打开一个笔记文件，再粘贴或拖入图片。"
            )
            return

        if isinstance(image_data, QImage):
            # 剪贴板图片：保存到 imgs 目录
            os.makedirs(self.imgs_dir, exist_ok=True)
            name = f"paste_{uuid.uuid4().hex[:8]}.png"
            dst = os.path.join(self.imgs_dir, name)
            if not image_data.save(dst, "PNG"):
                QMessageBox.warning(self, "错误", "剪贴板图片保存失败。")
                return
            self._insert_image_from_path(dst)
        elif isinstance(image_data, str) and os.path.isfile(image_data):
            self._insert_image_from_path(image_data)

    def _insert_image_from_path(self, path: str):
        """把指定图片文件复制到 imgs 目录并插入到编辑器。"""
        import shutil
        os.makedirs(self.imgs_dir, exist_ok=True)
        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        dst = os.path.join(self.imgs_dir, name)
        counter = 1
        while os.path.exists(dst):
            dst = os.path.join(self.imgs_dir, f"{base}_{counter}{ext}")
            counter += 1
        shutil.copy2(path, dst)
        rel = os.path.join("imgs", os.path.basename(dst)).replace("\\", "/")
        editor_width = self.editor.viewport().width()
        img_width = max(editor_width - 40, 200)
        # 对路径进行 HTML 转义，防止路径中包含特殊字符导致 XSS
        safe_rel = html.escape(rel, quote=True)
        img_html = f'<div style="display:block;"><img src="{safe_rel}" width="{img_width}"></div><br>'
        self.editor.textCursor().insertHtml(img_html)

    def _show_find_replace(self):
        if self._find_replace_dialog is None:
            self._find_replace_dialog = FindReplaceDialog(self.editor, self)
        self._find_replace_dialog.show()
        self._find_replace_dialog.raise_()
        self._find_replace_dialog.activateWindow()
        self._find_replace_dialog.find_edit.setFocus()

    def _on_export(self):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("导出 PDF", lambda: self.export_requested.emit("pdf"))
        menu.addAction("导出 HTML", lambda: self.export_requested.emit("html"))
        menu.addAction("导出 PNG", lambda: self.export_requested.emit("png"))
        menu.addAction("导出 SVG", lambda: self.export_requested.emit("svg"))
        btn = self.sender()
        if isinstance(btn, QPushButton):
            menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _on_editor_context_menu(self, pos):
        cursor = self.editor.cursorForPosition(pos)
        char_format = cursor.charFormat()
        is_image = char_format.isImageFormat()

        if is_image:
            self._show_image_context_menu(cursor, pos)

    def _show_image_context_menu(self, cursor, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ccc;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background: #007bff;
                color: white;
            }
        """)

        copy_action = QAction("复制图片", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self._on_copy_image(cursor))
        menu.addAction(copy_action)

        save_as_action = QAction("另存为...", self)
        save_as_action.triggered.connect(lambda: self._on_save_image_as(cursor))
        menu.addAction(save_as_action)

        menu.addSeparator()

        ocr_action = QAction("识别文字 (OCR)", self)
        ocr_action.triggered.connect(lambda: self._on_ocr_image(cursor))
        menu.addAction(ocr_action)

        menu.exec_(self.editor.mapToGlobal(pos))

    def _on_copy_image(self, cursor):
        try:
            char_format = cursor.charFormat()
            image = char_format.toImageFormat()

            if not image or not image.name():
                QMessageBox.warning(self, "错误", "无法获取图片信息")
                return

            image_path = self._find_image_file(image.name())

            if not image_path or not os.path.exists(image_path):
                QMessageBox.warning(self, "错误", f"图片文件不存在: {image.name()}")
                return

            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "错误", "无法加载图片")
                return

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制失败: {str(e)}")

    def _on_save_image_as(self, cursor):
        try:
            char_format = cursor.charFormat()
            image = char_format.toImageFormat()

            if not image or not image.name():
                QMessageBox.warning(self, "错误", "无法获取图片信息")
                return

            image_path = self._find_image_file(image.name())

            if not image_path or not os.path.exists(image_path):
                QMessageBox.warning(self, "错误", f"图片文件不存在: {image.name()}")
                return

            original_name = os.path.basename(image_path)

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "另存为",
                original_name,
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
            )

            if not file_path:
                return

            import shutil
            shutil.copy2(image_path, file_path)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    def _on_ocr_image(self, cursor):
        try:
            from ocr_manager import OCRManager, OCRThread

            char_format = cursor.charFormat()
            image = char_format.toImageFormat()

            if not image or not image.name():
                QMessageBox.warning(self, "错误", "无法获取图片信息")
                return

            image_path = self._find_image_file(image.name())

            if not image_path or not os.path.exists(image_path):
                QMessageBox.warning(self, "错误", f"图片文件不存在: {image.name()}")
                return

            ocr_manager = OCRManager()

            if not ocr_manager.is_configured():
                reply = QMessageBox.question(
                    self,
                    "OCR 配置",
                    "OCR 功能尚未配置，是否现在打开设置？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.settings_requested.emit()
                return

            # 非模态 loading 提示框，允许主线程继续处理事件
            progress = QMessageBox(self)
            progress.setWindowTitle("OCR 识别中")
            progress.setText("正在识别图片中的文字，请稍候...")
            progress.setStandardButtons(QMessageBox.NoButton)
            progress.setModal(False)
            progress.show()

            # 创建并启动 OCR 线程
            ocr_thread = OCRThread(ocr_manager, image_path)

            # 通过闭包保存上下文，方便在信号回调中使用
            def _on_ocr_finished(success, result, _cursor=cursor, _progress=progress, _thread=ocr_thread):
                try:
                    _progress.close()
                    if success:
                        # 对识别结果进行 HTML 转义，防止 XSS
                        safe_result = html.escape(result)
                        ocr_html = f'''
                        <div class="ocr-result" style="margin: 10px 0; padding: 8px; background: #f0f0f0; border-radius: 4px;">
                            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">识别结果：</div>
                            <div contenteditable="true" style="min-height: 20px; padding: 4px; background: white; border: 1px dashed #ccc;">
                                {safe_result}
                            </div>
                        </div>
                        '''
                        cur = _cursor
                        cur.movePosition(QTextCursor.EndOfBlock)
                        cur.insertBlock()
                        cur.insertHtml(ocr_html)
                        cur.insertBlock()
                    else:
                        QMessageBox.warning(self, "识别失败", result)
                finally:
                    # 清理线程引用
                    try:
                        self._ocr_threads.remove(_thread)
                    except ValueError:
                        pass
                    _thread.deleteLater()

            ocr_thread.ocr_ready.connect(_on_ocr_finished)
            self._ocr_threads.append(ocr_thread)
            ocr_thread.start()

        except Exception as e:
            logger.exception("OCR 启动失败: %s", e)
            QMessageBox.warning(self, "错误", f"OCR 失败: {str(e)}")

    def _find_image_file(self, image_name):
        if os.path.exists(image_name):
            return image_name

        if self.imgs_dir:
            rel_path = os.path.join(self.imgs_dir, image_name)
            if os.path.exists(rel_path):
                return rel_path

        current_dir_path = os.path.join(os.getcwd(), image_name)
        if os.path.exists(current_dir_path):
            return current_dir_path

        return None

    def _open_cloudcode_task(self):
        import uuid
        from cloudcode_dialog import CloudCodeTaskDialog

        dialog = CloudCodeTaskDialog(parent=self)
        if dialog.exec_() == CloudCodeTaskDialog.Accepted:
            task_data = dialog.get_task_data()
            task_id = f"task_{uuid.uuid4().hex[:8]}"

            self.status_update.emit(f"🚀 Cloud Code 任务启动 - {task_data['description'][:30]}...")

            success = self.cloudcode_executor.execute_task(
                task_id,
                task_data['description'],
                task_data['project_path'],
                self._on_task_completed
            )

            if not success:
                self.status_update.emit("❌ Cloud Code 任务启动失败")
                QMessageBox.warning(self, "错误", "任务执行失败")

    def _on_task_completed(self, task_id: str, task):
        if task.status == TaskStatus.COMPLETED:
            self.status_update.emit(f"✅ Cloud Code 任务完成 - {task.description[:30]}")
            result_dialog = CloudCodeResultDialog(task, self)
            result_dialog.exec_()
        elif task.status == TaskStatus.FAILED:
            self.status_update.emit(f"❌ Cloud Code 任务失败 - {task.description[:30]}")
            QMessageBox.warning(
                self, "任务失败",
                f"Cloud Code 任务执行失败\n\n错误：\n{task.stderr}"
            )

    def set_html(self, html: str):
        self.editor.blockSignals(True)
        self.editor.setHtml(html)
        self.editor.blockSignals(False)

    def to_html(self) -> str:
        return self.editor.toHtml()

    def is_modified(self) -> bool:
        return self.editor.document().isModified()

    def set_modified(self, modified: bool):
        self.editor.document().setModified(modified)
