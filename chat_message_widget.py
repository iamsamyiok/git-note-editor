from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QPainter, QColor, QFont

from chat_model import Message
from path_helper import get_default_font_family


class ChatMessageWidget(QFrame):
    selection_toggled = pyqtSignal(str, bool)

    def __init__(self, message: Message, parent=None):
        super().__init__(parent)
        self.message = message
        self._init_ui()
        self.update_selection_style()

    def _find_chat_widget(self):
        """向上遍历父级链找到 ChatWidget。"""
        p = self.parent()
        while p is not None:
            if hasattr(p, 'is_brush_mode'):
                return p
            p = p.parent()
        return None

    def _init_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        sender_color = "#007bff" if self.message.sender == "AI" else "#6c757d"
        sender_label = QLabel(self.message.sender)
        sender_label.setFont(QFont(get_default_font_family(), 9, QFont.Bold))
        sender_label.setStyleSheet(f"color: {sender_color};")
        header_layout.addWidget(sender_label)

        time_label = QLabel(self.message.timestamp)
        time_label.setStyleSheet("color: #999; font-size: 10px;")
        header_layout.addStretch()
        header_layout.addWidget(time_label)

        layout.addLayout(header_layout)

        content_label = QLabel(self.message.content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.PlainText)

        if self.message.sender == "AI":
            content_label.setStyleSheet("""
                QLabel {
                    background: #e3f2fd;
                    padding: 10px;
                    border-radius: 8px;
                    color: #333;
                    border: 1px solid #bbdefb;
                }
            """)
        else:
            content_label.setStyleSheet("""
                QLabel {
                    background: #f1f1f1;
                    padding: 10px;
                    border-radius: 8px;
                    color: #333;
                    border: 1px solid #ddd;
                }
            """)

        layout.addWidget(content_label)

    def enterEvent(self, event):
        chat_widget = self._find_chat_widget()
        if chat_widget and chat_widget.is_brush_mode:
            self.toggle_selection()
        super().enterEvent(event)

    def toggle_selection(self):
        # 不在本地切换状态；计算期望的新状态后由上层 ChatWidget 通过
        # chat_manager.toggle_message_selection 统一切换并落盘。
        # 信号是同步处理的，emit 返回后 message.is_selected 已被上层切换。
        new_state = not self.message.is_selected
        self.selection_toggled.emit(self.message.id, new_state)
        self.update_selection_style()

    def update_selection_style(self):
        if self.message.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background: #e8f4fd;
                    border-left: 4px solid #007bff;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            chat_widget = self._find_chat_widget()
            if not (chat_widget and chat_widget.is_brush_mode):
                self.toggle_selection()
        super().mousePressEvent(event)