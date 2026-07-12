import os
import json
from typing import List
from chat_model import ChatSession, Message
from json_store import JsonStore
from path_helper import get_data_file_path


class ChatManager:
    def __init__(self, data_file=None):
        if data_file is None:
            data_file = get_data_file_path("chat_sessions.json")
        self.data_file = data_file
        self.sessions: dict[str, ChatSession] = {}
        self.current_session_id: str = ""
        self._load_data()
    
    def _load_data(self):
        try:
            store = JsonStore(self.data_file)
            data = store.read(default={})
            if not isinstance(data, dict):
                data = {}
            for session_data in data.get('sessions', []):
                session = ChatSession.from_dict(session_data)
                self.sessions[session.id] = session
            self.current_session_id = data.get('current_session_id', '')
        except Exception as e:
            print(f"加载聊天数据失败: {e}")
            self.sessions = {}
            self.current_session_id = ""

    def _save_data(self):
        data = {
            'sessions': [session.to_dict() for session in self.sessions.values()],
            'current_session_id': self.current_session_id,
        }
        try:
            store = JsonStore(self.data_file)
            store.write(data)
        except Exception as e:
            print(f"保存聊天数据失败: {e}")
    
    def create_session(self, name: str = "新对话") -> ChatSession:
        session = ChatSession(name=name)
        self.sessions[session.id] = session
        self.current_session_id = session.id
        self._save_data()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        if self.current_session_id == session_id:
            self.current_session_id = ""
        self._save_data()
        return True
    
    def get_session(self, session_id: str) -> ChatSession | None:
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> ChatSession | None:
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        if self.sessions:
            self.current_session_id = next(iter(self.sessions.keys()))
            return self.sessions[self.current_session_id]
        return None
    
    def set_current_session(self, session_id: str):
        if session_id in self.sessions:
            self.current_session_id = session_id
            self._save_data()
    
    def get_all_sessions(self) -> List[ChatSession]:
        return list(self.sessions.values())
    
    def add_message(self, session_id: str, message: Message) -> bool:
        if session_id not in self.sessions:
            return False
        self.sessions[session_id].add_message(message)
        self._save_data()
        return True
    
    def toggle_message_selection(self, session_id: str, message_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        for msg in session.messages:
            if msg.id == message_id:
                msg.is_selected = not msg.is_selected
                self._save_data()
                return True
        return False
    
    def clear_selections(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        for msg in self.sessions[session_id].messages:
            msg.is_selected = False
        self._save_data()
        return True
    
    def get_selected_messages(self, session_id: str) -> List[Message]:
        if session_id not in self.sessions:
            return []
        return [msg for msg in self.sessions[session_id].messages if msg.is_selected]
    def delete_message(self, session_id: str, message_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        session.messages = [msg for msg in session.messages if msg.id != message_id]
        self._save_data()
        return True
