import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from models import CommitNode
from json_store import JsonStore

BRANCH_COLORS = [
    "#2196F3", "#FF5722", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#795548", "#607D8B",
]


class VersionManager:
    def __init__(self):
        self.repo_path = ""
        self.html_file = ""
        self.imgs_dir = ""
        self.note_dir = ""
        self.versions_dir = ""
        self.meta_file = ""
        self.current_commit = ""
        self._meta_cache = None
        self._meta_mtime = 0

    def _meta_path(self) -> str:
        return os.path.join(self.note_dir, "meta.json")

    def _version_path(self, commit_id: str) -> str:
        return os.path.join(self.versions_dir, f"{commit_id}.html")

    def _load_meta(self) -> dict:
        # 检查文件 mtime，未变化则返回缓存
        try:
            mtime = os.path.getmtime(self.meta_file) if os.path.exists(self.meta_file) else 0
        except OSError:
            mtime = 0

        if self._meta_cache is not None and mtime == self._meta_mtime:
            return self._meta_cache

        store = JsonStore(self.meta_file)
        raw = store.read(default=None)
        if not isinstance(raw, dict):
            raw = {}

        # 用 .get() 容错，确保缺字段不崩溃
        meta = {
            "commits": raw.get("commits", []),
            "branches": raw.get("branches", {}),
            "current_branch": raw.get("current_branch", "main"),
        }

        self._meta_cache = meta
        self._meta_mtime = mtime
        return meta

    def _save_meta(self, data: dict):
        store = JsonStore(self.meta_file)
        store.write(data)
        # 更新缓存
        self._meta_cache = data
        try:
            self._meta_mtime = os.path.getmtime(self.meta_file)
        except OSError:
            self._meta_mtime = 0

    def _new_id(self) -> str:
        return str(uuid.uuid4())[:8]

    # ---------- repo lifecycle ----------

    def init_repo(self, folder: str, html_filename: str) -> bool:
        self.repo_path = folder
        self.html_file = os.path.join(folder, html_filename)
        self.imgs_dir = os.path.join(folder, "imgs")
        self.note_dir = os.path.join(folder, ".note")
        self.versions_dir = os.path.join(self.note_dir, "versions")
        self.meta_file = os.path.join(self.note_dir, "meta.json")

        os.makedirs(folder, exist_ok=True)
        os.makedirs(self.imgs_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)

        root_id = self._new_id()
        stamp = datetime.now().strftime("%Y.%m.%d-%H:%M")
        root_html = "<html><body></body></html>"

        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(root_html)
        with open(self._version_path(root_id), "w", encoding="utf-8") as f:
            f.write(root_html)

        meta = {
            "commits": [{
                "id": root_id,
                "parent_id": None,
                "date": stamp,
                "message": f"{stamp}-根节点",
                "branch_name": "main",
                "is_root": True,
                "is_branch_start": False,
            }],
            "branches": {"main": root_id},
            "current_branch": "main",
        }
        self._save_meta(meta)
        self.current_commit = root_id
        return True

    def open_repo(self, html_path: str) -> Tuple[bool, str]:
        folder = os.path.dirname(os.path.abspath(html_path))
        note_dir = os.path.join(folder, ".note")
        meta_file = os.path.join(note_dir, "meta.json")

        if not os.path.isdir(note_dir) or not os.path.exists(meta_file):
            return False, "所选文件不是有效的笔记仓库。"

        self.repo_path = folder
        self.html_file = html_path
        self.imgs_dir = os.path.join(folder, "imgs")
        self.note_dir = note_dir
        self.versions_dir = os.path.join(note_dir, "versions")
        self.meta_file = meta_file

        os.makedirs(self.imgs_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)

        meta = self._load_meta()
        branch = meta.get("current_branch", "main")
        self.current_commit = meta["branches"].get(branch, "")

        return True, ""

    # ---------- commit ----------

    def commit(self, user_msg: str) -> Tuple[bool, str]:
        meta = self._load_meta()
        stamp = datetime.now().strftime("%Y.%m.%d-%H:%M")
        full_msg = f"{stamp}-{user_msg}"
        new_id = self._new_id()
        branch = meta["current_branch"]
        parent_id = self.current_commit if self.current_commit else meta["branches"].get(branch, "")

        current_html = ""
        if os.path.exists(self.html_file):
            with open(self.html_file, "r", encoding="utf-8") as f:
                current_html = f.read()

        with open(self._version_path(new_id), "w", encoding="utf-8") as f:
            f.write(current_html)

        parent_branch = ""
        if parent_id:
            parent_commit = self._find_commit(meta, parent_id)
            if parent_commit:
                parent_branch = parent_commit.get("branch_name", "")

        is_branch_start = False

        if branch != "main":
            if parent_branch == "main":
                is_branch_start = True
            elif not parent_id:
                is_branch_start = True

        commit_data = {
            "id": new_id,
            "parent_id": parent_id,
            "date": stamp,
            "message": full_msg,
            "branch_name": branch,
            "is_root": False,
            "is_branch_start": is_branch_start,
        }

        meta["commits"].append(commit_data)
        meta["branches"][branch] = new_id
        self._save_meta(meta)
        self.current_commit = new_id
        return True, new_id

    # ---------- branch ----------

    def create_branch(self, name: str, from_commit: str) -> Tuple[bool, str]:
        meta = self._load_meta()
        if name in meta["branches"]:
            return False, f"分支 {name} 已存在。"

        meta["branches"][name] = from_commit
        meta["current_branch"] = name
        self._save_meta(meta)

        from_file = self._version_path(from_commit)
        if os.path.exists(from_file):
            shutil.copy(from_file, self.html_file)

        self.current_commit = from_commit
        return True, ""

    def switch_branch(self, name: str) -> Tuple[bool, str]:
        meta = self._load_meta()
        if name not in meta["branches"]:
            return False, f"分支 {name} 不存在。"

        commit_id = meta["branches"][name]
        meta["current_branch"] = name
        self._save_meta(meta)

        ver_file = self._version_path(commit_id)
        if os.path.exists(ver_file):
            shutil.copy(ver_file, self.html_file)

        self.current_commit = commit_id
        return True, ""

    def checkout_commit(self, commit_hash: str) -> Tuple[bool, str]:
        meta = self._load_meta()
        commit = self._find_commit(meta, commit_hash)
        if not commit:
            return False, "提交不存在。"

        ver_file = self._version_path(commit_hash)
        if os.path.exists(ver_file):
            shutil.copy(ver_file, self.html_file)

        self.current_commit = commit_hash
        return True, ""

    def delete_commit(self, commit_hash: str) -> Tuple[bool, str]:
        meta = self._load_meta()
        commit = self._find_commit(meta, commit_hash)
        if not commit:
            return False, "提交不存在。"
        if commit.get("is_root"):
            return False, "根节点不可删除。"

        parent_id = commit.get("parent_id", "")
        # 找到所有子节点，逐一将 parent_id 改为被删除节点的 parent_id
        child_ids = [c["id"] for c in meta["commits"] if c.get("parent_id") == commit_hash]
        for c in meta["commits"]:
            if c.get("parent_id") == commit_hash:
                c["parent_id"] = parent_id

        meta["commits"] = [c for c in meta["commits"] if c["id"] != commit_hash]

        branch = meta.get("current_branch", "main")
        if meta["branches"].get(branch) == commit_hash:
            if child_ids:
                meta["branches"][branch] = child_ids[0]
            elif parent_id:
                meta["branches"][branch] = parent_id

        ver_file = self._version_path(commit_hash)
        if os.path.exists(ver_file):
            os.remove(ver_file)

        self._save_meta(meta)

        if child_ids:
            self.current_commit = child_ids[0]
        elif parent_id:
            self.current_commit = parent_id

        ver_file2 = self._version_path(self.current_commit)
        if os.path.exists(ver_file2):
            shutil.copy(ver_file2, self.html_file)

        return True, ""

    # ---------- query ----------

    def all_commits(self) -> Dict[str, CommitNode]:
        meta = self._load_meta()
        nodes: Dict[str, CommitNode] = {}

        for c in meta["commits"]:
            node = CommitNode(
                hash=c["id"],
                parent_hashes=[c["parent_id"]] if c.get("parent_id") else [],
                date=c["date"],
                message=c["message"],
                branch_name=c.get("branch_name", ""),
                is_root=c.get("is_root", False),
                is_branch_start=c.get("is_branch_start", False),
            )
            nodes[c["id"]] = node

        for c in meta["commits"]:
            pid = c.get("parent_id")
            if pid and pid in nodes and c["id"] in nodes:
                nodes[pid].children.append(c["id"])

        self._assign_lanes(nodes, meta)
        return nodes

    def current_branch(self) -> str:
        return self._load_meta().get("current_branch", "main")

    def current_hash(self) -> str:
        return self.current_commit

    def is_dirty(self) -> bool:
        return False

    def is_root(self, commit_hash: str) -> bool:
        meta = self._load_meta()
        c = self._find_commit(meta, commit_hash)
        return c.get("is_root", False) if c else False

    def repo_ok(self) -> bool:
        return bool(self.repo_path) and os.path.isdir(self.note_dir)

    # ---------- file IO ----------

    def read_html(self) -> str:
        if os.path.exists(self.html_file):
            with open(self.html_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def write_html(self, content: str):
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(content)

    def copy_image(self, src_path: str) -> str:
        os.makedirs(self.imgs_dir, exist_ok=True)
        name = os.path.basename(src_path)
        base, ext = os.path.splitext(name)
        dst = os.path.join(self.imgs_dir, name)
        counter = 1
        while os.path.exists(dst):
            dst = os.path.join(self.imgs_dir, f"{base}_{counter}{ext}")
            counter += 1
        shutil.copy2(src_path, dst)
        return os.path.join("imgs", os.path.basename(dst))

    def branches(self) -> List[str]:
        return list(self._load_meta().get("branches", {}).keys())

    # ---------- internal ----------

    def _build_commit_index(self, meta: dict) -> dict:
        """构建 id → commit_dict 索引。"""
        return {c.get("id"): c for c in meta.get("commits", []) if c.get("id")}

    def _find_commit(self, meta: dict, commit_id: str) -> Optional[dict]:
        index = self._build_commit_index(meta)
        return index.get(commit_id)

    def _assign_lanes(self, nodes: Dict[str, CommitNode], meta: dict):
        branches = meta.get("branches", {})

        for n in nodes.values():
            n.lane = 0

        main_commits = self._branch_ancestors(meta, "main")

        for h in main_commits:
            if h in nodes:
                nodes[h].lane = 0
                nodes[h].branch_name = "main"

        next_lane = 1
        for branch_name, tip in branches.items():
            if branch_name == "main":
                continue

            branch_commits = self._branch_ancestors(meta, branch_name)
            exclusive = branch_commits - main_commits
            if not exclusive:
                continue

            lane = next_lane
            next_lane += 1

            first = None
            for h in exclusive:
                if h in nodes:
                    node = nodes[h]
                    if node.parent_hashes and any(
                        p in main_commits for p in node.parent_hashes
                    ):
                        first = h

            for h in exclusive:
                if h in nodes:
                    nodes[h].lane = lane
                    nodes[h].branch_name = branch_name

            if first and first in nodes:
                nodes[first].is_branch_start = True

        commits = list(nodes.values())
        commits.sort(key=lambda c: c.date)
        for i, c in enumerate(commits):
            c.row = i
            if not c.parent_hashes:
                c.is_root = True

    def _branch_ancestors(self, meta: dict, branch_name: str) -> set:
        tip = meta.get("branches", {}).get(branch_name)
        if not tip:
            return set()

        ancestors = set()
        current = tip
        commit_map = {c["id"]: c for c in meta.get("commits", [])}

        while current and current in commit_map:
            ancestors.add(current)
            current = commit_map[current].get("parent_id", "")

        return ancestors
