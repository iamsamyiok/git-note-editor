from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QCheckBox, QPushButton, QMessageBox, QProgressDialog,
    QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class FetchTitleThread(QThread):
    title_fetched = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                self.title_fetched.emit(title)
            else:
                self.error_occurred.emit("无法获取网页标题")
        except Exception as e:
            self.error_occurred.emit(f"获取标题失败: {str(e)}")


class BookmarkDialog(QDialog):
    def __init__(self, categories, parent=None, bookmark=None):
        super().__init__(parent)
        self.categories = categories
        self.bookmark = bookmark
        self.setWindowTitle("添加网址" if not bookmark else "编辑网址")
        self.setMinimumWidth(450)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        url_layout = QVBoxLayout()
        url_label = QLabel("网址 URL:")
        url_layout.addWidget(url_label)
        
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("例如：https://www.google.com")
        self.url_input.textChanged.connect(self._on_url_changed)
        url_row.addWidget(self.url_input)
        
        fetch_btn = QPushButton("获取标题")
        fetch_btn.clicked.connect(self._fetch_title)
        fetch_btn.setFixedWidth(80)
        url_row.addWidget(fetch_btn)
        
        url_layout.addLayout(url_row)
        layout.addLayout(url_layout)
        
        title_layout = QVBoxLayout()
        title_label = QLabel("标题:")
        title_layout.addWidget(title_label)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("网页标题")
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        desc_layout = QVBoxLayout()
        desc_label = QLabel("描述:")
        desc_layout.addWidget(desc_label)
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText="备注信息（可选）"
        self.desc_input.setMaximumHeight(80)
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)
        
        category_layout = QVBoxLayout()
        category_label = QLabel("分类:")
        category_layout.addWidget(category_label)
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        tags_layout = QVBoxLayout()
        tags_label = QLabel("标签（用逗号分隔）:")
        tags_layout.addWidget(tags_label)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText="例如：搜索,工具,必备"
        tags_layout.addWidget(self.tags_input)
        layout.addLayout(tags_layout)
        
        self.fav_check = QCheckBox("设为收藏")
        layout.addWidget(self.fav_check)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
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
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if self.bookmark:
            self._load_bookmark_data()
    
    def _load_bookmark_data(self):
        self.url_input.setText(self.bookmark.url)
        self.title_input.setText(self.bookmark.title)
        self.desc_input.setText(self.bookmark.description)
        self.category_combo.setCurrentText(self.bookmark.category)
        self.tags_input.setText(", ".join(self.bookmark.tags))
        self.fav_check.setChecked(self.bookmark.is_favorite)
    
    def _on_url_changed(self, text):
        if not self.title_input.text():
            if not text.startswith("http"):
                return
            self.title_input.setText(text)
    
    def _fetch_title(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请先输入网址！")
            return
        
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        progress = QProgressDialog("正在获取网页标题...", "取消", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        self.fetch_thread = FetchTitleThread(url)
        self.fetch_thread.title_fetched.connect(self._on_title_fetched)
        self.fetch_thread.error_occurred.connect(self._on_fetch_error)
        self.fetch_thread.start()
    
    def _on_title_fetched(self, title):
        self.title_input.setText(title)
        self.close_progress()
    
    def _on_fetch_error(self, error):
        QMessageBox.warning(self, "错误", error)
        self.close_progress()
    
    def close_progress(self):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
    
    def get_bookmark_data(self):
        tags_text = self.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()] if tags_text else []
        
        return {
            'title': self.title_input.text().strip(),
            'url': self.url_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'category': self.category_combo.currentText(),
            'tags': tags,
            'is_favorite': self.fav_check.isChecked(),
        }