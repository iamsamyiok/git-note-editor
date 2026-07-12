import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction,
    QTextEdit, QFileDialog, QColorDialog, QInputDialog,
)
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QTextListFormat, QImage
from PyQt5.QtCore import Qt, pyqtSignal


class EditorWidget(QWidget):
    content_changed = pyqtSignal()

    def __init__(self, imgs_dir=""):
        super().__init__()
        self.imgs_dir = imgs_dir

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        self._setup_toolbar()
        layout.addWidget(self.toolbar)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.textChanged.connect(self.content_changed.emit)
        layout.addWidget(self.editor)

    def _setup_toolbar(self):
        actions = [
            ("bold", "B", True, "加粗"),
            ("italic", "I", True, "斜体"),
            ("underline", "U", True, "下划线"),
            (None, None, False, ""),
            ("color", "A", False, "文字颜色"),
            ("bgcolor", "BG", False, "背景色"),
            (None, None, False, ""),
            ("left", "L", False, "左对齐"),
            ("center", "C", False, "居中"),
            ("right", "R", False, "右对齐"),
            ("justify", "J", False, "两端对齐"),
            (None, None, False, ""),
            ("ulist", "UL", False, "无序列表"),
            ("olist", "OL", False, "有序列表"),
            (None, None, False, ""),
            ("table", "Tab", False, "插入表格"),
            ("link", "Link", False, "超链接"),
            ("image", "Img", False, "插入图片"),
        ]

        for action_id, label, checkable, tip in actions:
            if action_id is None:
                self.toolbar.addSeparator()
                continue

            if checkable:
                act = QAction(label, self)
                act.setCheckable(True)
                act.setToolTip(tip)
                act.toggled.connect(lambda c, a=action_id: self._on_format(a, c))
            else:
                act = QAction(label, self)
                act.setToolTip(tip)
                act.triggered.connect(lambda _, a=action_id: self._on_action(a))

            self.toolbar.addAction(act)

    def _on_format(self, fmt: str, checked: bool):
        cf = QTextCharFormat()
        if fmt == "bold":
            cf.setFontWeight(QFont.Bold if checked else QFont.Normal)
            self.editor.mergeCurrentCharFormat(cf)
        elif fmt == "italic":
            cf.setFontItalic(checked)
            self.editor.mergeCurrentCharFormat(cf)
        elif fmt == "underline":
            cf.setFontUnderline(checked)
            self.editor.mergeCurrentCharFormat(cf)

    def _on_action(self, action: str):
        cursor = self.editor.textCursor()

        if action == "color":
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
            url = QInputDialog.getText(self, "插入超链接", "URL:")
            if url[1] and url[0]:
                cursor.insertHtml(
                    f'<a href="{url[0]}">{url[0]}</a>'
                )
        elif action == "image":
            self._insert_image()

    def _insert_table(self):
        rows, ok1 = QInputDialog.getInt(self, "插入表格", "行数：", 3, 1, 20, 1)
        if not ok1:
            return
        cols, ok2 = QInputDialog.getInt(self, "插入表格", "列数：", 3, 1, 10, 1)
        if not ok2:
            return

        html = '<table border="1" cellspacing="0" cellpadding="4">'
        for _ in range(rows):
            html += "<tr>"
            for _ in range(cols):
                html += "<td>&nbsp;</td>"
            html += "</tr>"
        html += "</table>"

        self.editor.textCursor().insertHtml(html)

    def _insert_image(self):
        if not self.imgs_dir:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if not path:
            return

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

        rel = os.path.join("imgs", os.path.basename(dst))
        rel = rel.replace("\\", "/")

        editor_width = self.editor.viewport().width()
        img_width = max(editor_width - 40, 200)

        html = f'<div><img src="{rel}" width="{img_width}"></div>'
        self.editor.textCursor().insertHtml(html)

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
