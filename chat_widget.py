import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QScrollArea, QMessageBox, QFrame,
    QListWidget, QListWidgetItem, QToolButton, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

from chat_manager import ChatManager
from chat_model import Message
from chat_message_widget import ChatMessageWidget
from ai_service import AIService


class ChatWidget(QWidget):
    export_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_manager = ChatManager()
        self.ai_service = AIService()
        self.is_brush_mode = False
        
        self._init_ui()
        self._load_session()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 10, 10, 8)
        top_bar.setSpacing(10)
        
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        self.session_combo.setFixedWidth(200)
        top_bar.addWidget(self.session_combo)
        
        new_session_btn = QPushButton("＋ 新对话")
        new_session_btn.setFixedHeight(30)
        new_session_btn.clicked.connect(self._create_new_session)
        new_session_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        top_bar.addWidget(new_session_btn)
        
        delete_session_btn = QPushButton("删除对话")
        delete_session_btn.setFixedHeight(30)
        delete_session_btn.clicked.connect(self._delete_session)
        delete_session_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        top_bar.addWidget(delete_session_btn)
        
        top_bar.addStretch()
        
        self.brush_btn = QPushButton("🖌️ 笔刷模式")
        self.brush_btn.setFixedHeight(30)
        self.brush_btn.setCheckable(True)
        self.brush_btn.clicked.connect(self._toggle_brush_mode)
        self.brush_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
            QPushButton:checked {
                background: #007bff;
            }
        """)
        top_bar.addWidget(self.brush_btn)
        
        self.selection_count_label = QLabel("已选: 0 条")
        self.selection_count_label.setStyleSheet("color: #999; font-size: 12px;")
        top_bar.addWidget(self.selection_count_label)
        
        export_btn = QPushButton("📤 导出选中")
        export_btn.setFixedHeight(30)
        export_btn.clicked.connect(self._export_selected)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        top_bar.addWidget(export_btn)
        
        layout.addLayout(top_bar)
        
        message_scroll = QScrollArea()
        message_scroll.setWidgetResizable(True)
        message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(10, 10, 10, 10)
        self.message_layout.setSpacing(12)
        self.message_layout.addStretch()
        
        message_scroll.setWidget(self.message_container)
        layout.addWidget(message_scroll)
        
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border-top: 1px solid #ddd;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...（按 Enter 发送）")
        self.message_input.setFixedHeight(40)
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #007bff;
            }
        """)
        self.message_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.message_input)
        
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        
        send_btn = QPushButton("发送")
        send_btn.setFixedHeight(32)
        send_btn.clicked.connect(self._send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        button_row.addWidget(send_btn)
        
        ai_reply_btn = QPushButton("🤖 AI 回复")
        ai_reply_btn.setFixedHeight(32)
        ai_reply_btn.clicked.connect(self._trigger_ai_reply)
        ai_reply_btn.setStyleSheet("""
            QPushButton {
                background: #6610f2;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #520dc2;
            }
        """)
        button_row.addWidget(ai_reply_btn)
        
        button_row.addStretch()
        
        hint_label = QLabel("提示：未选中消息时 AI 基于最近对话回复，选中消息时基于选中内容")
        hint_label.setStyleSheet("color: #999; font-size: 10px;")
        button_row.addWidget(hint_label)
        
        input_layout.addLayout(button_row)
        
        layout.addWidget(input_container)
    
    def _load_session(self):
        sessions = self.chat_manager.get_all_sessions()
        self.session_combo.clear()
        
        if not sessions:
            self.chat_manager.create_session()
            sessions = self.chat_manager.get_all_sessions()
        
        for session in sessions:
            self.session_combo.addItem(session.name, session.id)
        
        current = self.chat_manager.get_current_session()
        if current:
            idx = self.session_combo.findData(current.id)
            if idx >= 0:
                self.session_combo.setCurrentIndex(idx)
        
        self._refresh_messages()
    
    def _on_session_changed(self, index):
        session_id = self.session_combo.itemData(index)
        if session_id:
            self.chat_manager.set_current_session(session_id)
            self._refresh_messages()
    
    def _create_new_session(self):
        name, ok = QInputDialog.getText(self, "新建对话", "对话名称:")
        if ok and name.strip():
            self.chat_manager.create_session(name.strip())
            self._load_session()
    
    def _delete_session(self):
        current = self.chat_manager.get_current_session()
        if not current:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除「{current.name}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.chat_manager.delete_session(current.id)
            self._load_session()
    
    def _refresh_messages(self):
        for i in reversed(range(self.message_layout.count())):
            widget = self.message_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        current = self.chat_manager.get_current_session()
        if not current:
            return
        
        for msg in current.messages:
            msg_widget = ChatMessageWidget(msg)
            msg_widget.selection_toggled.connect(self._on_message_toggled)
            self.message_layout.insertWidget(self.message_layout.count() - 1, msg_widget)
        
        self._scroll_to_bottom()
    
    def _on_message_toggled(self, message_id: str, selected: bool):
        self.update_selection_count()
    
    def update_selection_count(self):
        current = self.chat_manager.get_current_session()
        if not current:
            count = 0
        else:
            count = sum(1 for msg in current.messages if msg.is_selected)
        
        self.selection_count_label.setText(f"已选: {count} 条")
    
    def _toggle_brush_mode(self):
        self.is_brush_mode = self.brush_btn.isChecked()
        
        if self.is_brush_mode:
            self.setCursor(Qt.CrossCursor)
            self.message_input.setReadOnly(True)
            self.message_input.setPlaceholderText("笔刷模式：滑动选择消息（已禁用输入）")
        else:
            self.setCursor(Qt.ArrowCursor)
            self.message_input.setReadOnly(False)
            self.message_input.setPlaceholderText("输入消息...（按 Enter 发送）")
    
    def _send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return
        
        current = self.chat_manager.get_current_session()
        if not current:
            QMessageBox.warning(self, "错误", "没有活动对话")
            return
        
        message = Message(
            session_id=current.id,
            sender="用户",
            content=text,
            message_type="text"
        )
        
        self.chat_manager.add_message(current.id, message)
        self._refresh_messages()
        self.message_input.clear()
    
    def _trigger_ai_reply(self):
        current = self.chat_manager.get_current_session()
        if not current:
            QMessageBox.warning(self, "错误", "没有活动对话")
            return
        
        selected_messages = [msg for msg in current.messages if msg.is_selected]
        
        if not selected_messages:
            context_messages = current.messages
        else:
            context_messages = selected_messages
        
        loading_msg = Message(
            session_id=current.id,
            sender="AI",
            content="🤔 正在思考...",
            message_type="system"
        )
        
        self.chat_manager.add_message(current.id, loading_msg)
        self._refresh_messages()
        
        success, result = self.ai_service.generate_reply(context_messages)
        
        if not self.chat_manager.delete_message(current.id, loading_msg.id):
            self._refresh_messages()
        
        if success:
            ai_message = Message(
                session_id=current.id,
                sender="AI",
                content=result,
                message_type="text"
            )
            
            self.chat_manager.add_message(current.id, ai_message)
            self._refresh_messages()
        else:
            QMessageBox.warning(self, "AI 回复失败", result)
    
    def _export_selected(self):
        current = self.chat_manager.get_current_session()
        if not current:
            QMessageBox.warning(self, "错误", "没有活动对话")
            return
        
        selected_messages = [msg for msg in current.messages if msg.is_selected]
        
        if not selected_messages:
            QMessageBox.warning(self, "提示", "请先选择要导出的消息")
            return
        
        exported_content = ""
        for msg in selected_messages:
            header = f"**{msg.sender}** ({msg.timestamp})\n"
            exported_content += header + msg.content + "\n\n"
        
        self.export_requested.emit(exported_content)
        QMessageBox.information(self, "成功", f"已导出 {len(selected_messages)} 条消息到笔记")
    
    def _scroll_to_bottom(self):
        scroll = self.message_container.parent().verticalScrollBar()
        if scroll:
            scroll.setValue(scroll.maximum())