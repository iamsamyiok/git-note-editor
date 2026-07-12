import os
import json
from bookmark_model import Bookmark
from json_store import JsonStore
from path_helper import get_data_file_path


class BookmarkManager:
    def __init__(self, data_file=None):
        self.data_file = data_file or get_data_file_path("bookmarks.json")
        self.bookmarks: dict[str, Bookmark] = {}
        self.categories = ["全部", "默认分类", "工作相关", "学习资料", "娱乐休闲", "工具"]
        self._load_data()
    
    def _load_data(self):
        try:
            store = JsonStore(self.data_file)
            data = store.read(default={})
            if not isinstance(data, dict):
                data = {}
            for bookmark_data in data.get('bookmarks', []):
                bookmark = Bookmark.from_dict(bookmark_data)
                self.bookmarks[bookmark.id] = bookmark
            if 'categories' in data:
                self.categories = data['categories']
        except Exception as e:
            print(f"加载收藏数据失败: {e}")
            self.bookmarks = {}
            self.categories = ["全部", "默认分类", "工作相关", "学习资料", "娱乐休闲", "工具"]

    def _save_data(self):
        data = {
            'bookmarks': [bookmark.to_dict() for bookmark in self.bookmarks.values()],
            'categories': self.categories
        }
        try:
            store = JsonStore(self.data_file)
            store.write(data)
        except Exception as e:
            print(f"保存收藏数据失败: {e}")
    
    def add_bookmark(self, bookmark: Bookmark) -> bool:
        if bookmark.id in self.bookmarks:
            return False
        self.bookmarks[bookmark.id] = bookmark
        self._save_data()
        return True
    
    def update_bookmark(self, bookmark: Bookmark) -> bool:
        if bookmark.id not in self.bookmarks:
            return False
        bookmark.update_timestamp()
        self.bookmarks[bookmark.id] = bookmark
        self._save_data()
        return True
    
    def delete_bookmark(self, bookmark_id: str) -> bool:
        if bookmark_id not in self.bookmarks:
            return False
        del self.bookmarks[bookmark_id]
        self._save_data()
        return True
    
    def get_bookmark(self, bookmark_id: str) -> Bookmark | None:
        return self.bookmarks.get(bookmark_id)
    
    def get_all_bookmarks(self) -> list[Bookmark]:
        return list(self.bookmarks.values())
    
    def get_bookmarks_by_category(self, category: str) -> list[Bookmark]:
        if category == "全部":
            return self.get_all_bookmarks()
        return [b for b in self.bookmarks.values() if b.category == category]
    
    def search_bookmarks(self, query: str) -> list[Bookmark]:
        query = query.lower()
        results = []
        for bookmark in self.bookmarks.values():
            if (query in bookmark.title.lower() or 
                query in bookmark.url.lower() or 
                query in bookmark.description.lower() or
                any(query in tag.lower() for tag in bookmark.tags)):
                results.append(bookmark)
        return results
    
    def get_favorite_bookmarks(self) -> list[Bookmark]:
        return [b for b in self.bookmarks.values() if b.is_favorite]
    
    def toggle_favorite(self, bookmark_id: str) -> bool:
        if bookmark_id not in self.bookmarks:
            return False
        bookmark = self.bookmarks[bookmark_id]
        bookmark.is_favorite = not bookmark.is_favorite
        bookmark.update_timestamp()
        self._save_data()
        return True
    
    def add_category(self, category: str) -> bool:
        if category in self.categories:
            return False
        self.categories.append(category)
        self._save_data()
        return True
    
    def get_categories(self) -> list[str]:
        return self.categories.copy()
    
    def increment_visit_count(self, bookmark_id: str) -> bool:
        if bookmark_id not in self.bookmarks:
            return False
        bookmark = self.bookmarks[bookmark_id]
        bookmark.increment_visit_count()
        self._save_data()
        return True