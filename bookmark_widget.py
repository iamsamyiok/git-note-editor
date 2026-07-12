import webbrowser
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QLineEdit, QComboBox, QMenu, QMessageBox,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QPixmap

from bookmark_manager import BookmarkManager


class BookmarkListWidget(QListWidget):
    bookmark_clicked = pyqtSignal(object)
    bookmark_double_clicked = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.bookmarks = {}
    
    def update_bookmarks(self, bookmarks):
        self.clear()
        self.bookmarks = {}
        
        for bookmark in bookmarks:
            item = QListWidgetItem()
            widget = BookmarkItemWidget(bookmark)
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, bookmark)
            self.bookmarks[bookmark.id] = item
    
    def _on_item_clicked(self, item):
        bookmark = self.itemWidget(item)
        if bookmark:
            self.bookmark_clicked.emit(bookmark)
    
    def _on_item_double_clicked(self, item):
        bookmark = self.itemWidget(item)
        if bookmark:
            self.bookmark_double_clicked.emit(bookmark)
    
    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return
        
        bookmark = self.itemWidget(item)
        menu = QMenu(self)
        
        open_action = menu.addAction("🌐 在浏览器中打开")
        open_action.triggered.connect(lambda: self._open_bookmark(bookmark))
        
        menu.addSeparator()
        
        edit_action = menu.addAction("✏️ 编辑")
        edit_action.triggered.connect(lambda: self.parent().parent()._edit_bookmark(bookmark))
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self.parent().parent()._delete_bookmark(bookmark))
        
        menu.addSeparator()
        
        fav_action = menu.addAction("⭐ 取消收藏" if bookmark.is_favorite else "⭐ 收藏")
        fav_action.triggered.connect(lambda: self.parent().parent()._toggle_favorite(bookmark))
        
        menu.exec_(self.mapToGlobal(pos))
    
    def _open_bookmark(self, bookmark):
        webbrowser.open(bookmark.url)
        self.parent().parent().bookmark_manager.increment_visit_count(bookmark.id)
        self.parent().parent()._refresh_list()


class BookmarkItemWidget(QWidget):
    def __init__(self, bookmark, parent=None):
        super().__init__(parent)
        self.bookmark = bookmark
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)
        
        fav_icon = QLabel("⭐" if self.bookmark.is_favorite else "")
        fav_icon.setStyleSheet("color: #FFD700; font-size: 14px;")
        title_layout.addWidget(fav_icon)
        
        title_label = QLabel(self.bookmark.title)
        title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title_label.setStyleSheet("color: #333;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        visit_label = QLabel(f"🔍 {self.bookmark.visit_count}")
        visit_label.setStyleSheet("color: #999; font-size: 10px;")
        title_layout.addWidget(visit_label)
        
        layout.addLayout(title_layout)
        
        url_label = QLabel(self.bookmark.url)
        url_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(url_label)
        
        if self.bookmark.description:
            desc_label = QLabel(self.bookmark.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #999; font-size: 9px;")
            desc_label.setMaximumHeight(40)
            layout.addWidget(desc_label)
        
        if self.bookmark.tags:
            tags_label = QLabel("  ".join(f"#{tag}" for tag in self.bookmark.tags))
            tags_label.setStyleSheet("color: #6699CC; font-size: 8px;")
            layout.addWidget(tags_label)


class BookmarkWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bookmark_manager = BookmarkManager()
        self.current_category = "全部"
        self._init_ui()
        self._refresh_list()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 5, 10)
        left_layout.setSpacing(10)
        left_panel.setMaximumWidth(200)
        
        category_label = QLabel("分类筛选")
        category_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        left_layout.addWidget(category_label)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.bookmark_manager.get_categories())
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        left_layout.addWidget(self.category_combo)
        
        add_category_btn = QPushButton("＋ 添加分类")
        add_category_btn.clicked.connect(self._add_category)
        add_category_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        left_layout.addWidget(add_category_btn)
        
        left_layout.addStretch()
        
        left_layout.addWidget(QLabel("快捷键："))
        short_hint = QLabel("Ctrl+Shift+A\n打开收藏面板")
        short_hint.setStyleSheet("color: #999; font-size: 9px;")
        left_layout.addWidget(short_hint)
        
        layout.addWidget(left_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 10, 10, 10)
        right_layout.setSpacing(10)
        
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索网址、标题、描述、标签...")
        search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(search_input)
        
        add_btn = QPushButton("＋ 添加网址")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 6px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        add_btn.clicked.connect(self._add_bookmark)
        top_bar.addWidget(add_btn)
        
        right_layout.addLayout(top_bar)
        
        self.bookmark_list = BookmarkListWidget()
        right_layout.addWidget(self.bookmark_list)
        
        self.bookmark_list.bookmark_clicked.connect(self._on_bookmark_clicked)
        self.bookmark_list.bookmark_double_clicked.connect(self._on_bookmark_double_clicked)
        
        layout.addWidget(right_panel)
    
    def _on_category_changed(self, category):
        self.current_category = category
        self._refresh_list()
    
    def _add_category(self):
        from PyQt5.QtWidgets import QInputDialog
        
        category, ok = QInputDialog.getText(
            self, "添加分类", "请输入分类名称:"
        )
        
        if ok and category.strip():
            if self.bookmark_manager.add_category(category.strip()):
                self.category_combo.addItem(category.strip())
                QMessageBox.information(self, "成功", "分类添加成功！")
            else:
                QMessageBox.warning(self, "警告", "分类已存在！")
    
    def _on_search_changed(self, text):
        if text.strip():
            bookmarks = self.bookmark_manager.search_bookmarks(text)
        else:
            bookmarks = self.bookmark_manager.get_bookmarks_by_category(self.current_category)
        
        self.bookmark_list.update_bookmarks(bookmarks)
    
    def _add_bookmark(self):
        from bookmark_dialog import BookmarkDialog
        
        dialog = BookmarkDialog(self.bookmark_manager.get_categories(), self)
        if dialog.exec_() == BookmarkDialog.Accepted:
            bookmark_data = dialog.get_bookmark_data()
            
            from bookmark_model import Bookmark
            bookmark = Bookmark(
                title=bookmark_data['title'],
                url=bookmark_data['url'],
                description=bookmark_data['description'],
                category=bookmark_data['category'],
                tags=bookmark_data['tags'],
                is_favorite=bookmark_data['is_favorite']
            )
            
            if self.bookmark_manager.add_bookmark(bookmark):
                self._refresh_list()
                QMessageBox.information(self, "成功", "网址收藏成功！")
            else:
                QMessageBox.warning(self, "错误", "添加失败！")
    
    def _edit_bookmark(self, bookmark):
        from bookmark_dialog import BookmarkDialog
        
        dialog = BookmarkDialog(self.bookmark_manager.get_categories(), self, bookmark)
        if dialog.exec_() == BookmarkDialog.Accepted:
            bookmark_data = dialog.get_bookmark_data()
            
            bookmark.title = bookmark_data['title']
            bookmark.url = bookmark_data['url']
            bookmark.description = bookmark_data['description']
            bookmark.category = bookmark_data['category']
            bookmark.tags = bookmark_data['tags']
            bookmark.is_favorite = bookmark_data['is_favorite']
            
            if self.bookmark_manager.update_bookmark(bookmark):
                self._refresh_list()
                QMessageBox.information(self, "成功", "网址更新成功！")
            else:
                QMessageBox.warning(self, "错误", "更新失败！")
    
    def _delete_bookmark(self, bookmark):
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除「{bookmark.title}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.bookmark_manager.delete_bookmark(bookmark.id):
                self._refresh_list()
                QMessageBox.information(self, "成功", "删除成功！")
            else:
                QMessageBox.warning(self, "错误", "删除失败！")
    
    def _toggle_favorite(self, bookmark):
        if self.bookmark_manager.toggle_favorite(bookmark.id):
            self._refresh_list()
    
    def _on_bookmark_clicked(self, bookmark):
        pass
    
    def _on_bookmark_double_clicked(self, bookmark):
        webbrowser.open(bookmark.url)
        self.bookmark_manager.increment_visit_count(bookmark.id)
        self._refresh_list()
    
    def _refresh_list(self):
        bookmarks = self.bookmark_manager.get_bookmarks_by_category(self.current_category)
        
        text = ""
        if hasattr(self, 'bookmark_list'):
            if hasattr(self.bookmark_list.parent(), 'parent'):
                top_bar = self.bookmark_list.parent().parent().findChild(QLineEdit)
                if top_bar:
                    text = top_bar.text().strip()
        
        if text:
            bookmarks = self.bookmark_manager.search_bookmarks(text)
        
        self.bookmark_list.update_bookmarks(bookmarks)