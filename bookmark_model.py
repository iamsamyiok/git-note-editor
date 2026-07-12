from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid


@dataclass
class Bookmark:
    id: str
    title: str
    url: str
    description: str = ""
    category: str = "默认分类"
    tags: List[str] = field(default_factory=list)
    is_favorite: bool = False
    visit_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'category': self.category,
            'tags': self.tags,
            'is_favorite': self.is_favorite,
            'visit_count': self.visit_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            url=data.get('url', ''),
            description=data.get('description', ''),
            category=data.get('category', '默认分类'),
            tags=data.get('tags', []),
            is_favorite=data.get('is_favorite', False),
            visit_count=data.get('visit_count', 0),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
        )
    
    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()
    
    def increment_visit_count(self):
        self.visit_count += 1
        self.update_timestamp()