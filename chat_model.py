from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid


@dataclass
class Message:
    id: str
    session_id: str
    sender: str
    content: str
    message_type: str = "text"
    timestamp: str = ""
    is_selected: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M")
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'sender': self.sender,
            'content': self.content,
            'message_type': self.message_type,
            'timestamp': self.timestamp,
            'is_selected': self.is_selected,
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id', ''),
            session_id=data.get('session_id', ''),
            sender=data.get('sender', ''),
            content=data.get('content', ''),
            message_type=data.get('message_type', 'text'),
            timestamp=data.get('timestamp', ''),
            is_selected=data.get('is_selected', False),
        )


@dataclass
class ChatSession:
    id: str
    name: str
    created_at: str = ""
    updated_at: str = ""
    messages: List[Message] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'messages': [msg.to_dict() for msg in self.messages],
        }
    
    @classmethod
    def from_dict(cls, data):
        session = cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
        )
        for msg_data in data.get('messages', []):
            session.messages.append(Message.from_dict(msg_data))
        return session