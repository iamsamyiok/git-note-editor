import os
import subprocess
import glob
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models import CommitNode, BranchInfo

BRANCH_COLORS = [
    "#2196F3", "#FF5722", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#795548", "#607D8B",
]


class GitManager:
    def __init__(self):
        self.repo_path = ""
        self.html_file = ""
        self.imgs_dir = ""

    # ---------- repo lifecycle ----------

    def init_repo(self, folder: str, html_filename: str) -> bool:
        self.repo_path = folder
        self.html_file = os.path.join(folder, html_filename)
        self.imgs_dir = os.path.join(folder, "imgs")

        os.makedirs(folder, exist_ok=True)
        os.makedirs(self.imgs_dir, exist_ok=True)

        self._run("init", "-b", "main")
        self._run("config", "user.email", "note@git.local")
        self._run("config", "user.name", "GitNote")

        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")

        stamp = datetime.now().strftime("%Y.%m.%d-%H:%M")
        msg = f"{stamp}-根节点"
        self._run("add", ".")
        self._run("commit", "-m", msg)
        return True

    def open_repo(self, html_path: str) -> Tuple[bool, str]:
        folder = os.path.dirname(os.path.abspath(html_path))
        git_dir = os.path.join(folder, ".git")
        if not os.path.isdir(git_dir):
            return False, "所选目录不是有效的 Git 仓库。"
        if not os.path.exists(os.path.join(git_dir, "HEAD")):
            repaired = self._fsck_repair_internal(folder)
            if not repaired:
                return False, "仓库损坏，无法打开。"
        self.repo_path = folder
        self.html_file = html_path
        self.imgs_dir = os.path.join(folder, "imgs")
        os.makedirs(self.imgs_dir, exist_ok=True)
        self._ensure_identity()
        return True, ""

    # ---------- commit ----------

    def commit(self, user_msg: str) -> Tuple[bool, str]:
        stamp = datetime.now().strftime("%Y.%m.%d-%H:%M")
        full_msg = f"{stamp}-{user_msg}"
        self._run("add", ".")
        code, out, err = self._run("commit", "-m", full_msg)
        if code != 0:
            if "nothing to commit" in (out + err).lower():
                return False, "没有需要提交的变更。"
            return False, err or out
        return True, self._latest_hash()

    # ---------- branch ----------

    def create_branch(self, name: str, from_commit: str) -> Tuple[bool, str]:
        branches = self._branches()
        if name in branches:
            return False, f"分支 {name} 已存在。"
        code, _, err = self._run("branch", name, from_commit)
        if code != 0:
            return False, err
        return True, ""

    def switch_branch(self, name: str) -> Tuple[bool, str]:
        code, _, err = self._run("checkout", name)
        if code != 0:
            return False, err
        return True, ""

    def checkout_commit(self, commit_hash: str) -> Tuple[bool, str]:
        code, _, err = self._run("checkout", commit_hash)
        if code != 0:
            return False, err
        return True, ""

    def delete_commit(self, commit_hash: str) -> Tuple[bool, str]:
        parent = self._parent_of(commit_hash)
        if not parent:
            return False, "根节点不可删除。"

        branch = self._current_branch()
        if not branch:
            return False, "HEAD 未关联分支。"

        if self.is_dirty():
            return False, "工作区存在未提交的变更，请先提交或丢弃。"

        saved_branch = branch

        try:
            children = self._children_of(commit_hash, branch)

            self._run("reset", "--soft", parent)
            code, out, err = self._run("commit", "-m", "remove intermediate")
            if code != 0:
                self._run("reset", "--hard", f"ORIG_HEAD")
                return False, (err or out)[:200]

            for child_hash in children[1:]:
                code, out, err = self._run("cherry-pick", child_hash)
                if code != 0:
                    self._run("cherry-pick", "--abort")
                    return False, f"无法重放提交 {child_hash[:8]}"

            return True, ""
        except Exception as e:
            try:
                self._run("checkout", saved_branch)
            except Exception:
                pass
            return False, str(e)

    # ---------- query ----------

    def all_commits(self) -> Dict[str, CommitNode]:
        out = self._run_out("log", "--all", "--reverse",
                             "--format=%H|%P|%aI|%s|%D")
        nodes: Dict[str, CommitNode] = {}
        for line in out.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            h = parts[0]
            parents = [p for p in parts[1].split() if p]
            nodes[h] = CommitNode(
                hash=h,
                parent_hashes=parents,
                date=parts[2],
                message=parts[3],
                refs=self._parse_refs(parts[4]),
            )

        for h, node in nodes.items():
            for p in node.parent_hashes:
                if p in nodes:
                    nodes[p].children.append(h)

        commits = list(nodes.values())
        commits.sort(key=lambda c: c.date)
        for i, c in enumerate(commits):
            c.row = i
            if not c.parent_hashes:
                c.is_root = True

        self._assign_branches(nodes)
        return nodes

    def current_branch(self) -> str:
        return self._current_branch()

    def current_hash(self) -> str:
        return self._run_out("rev-parse", "HEAD").strip()

    def is_dirty(self) -> bool:
        code = self._run_code("diff", "--quiet")
        return code != 0

    def is_root(self, commit_hash: str) -> bool:
        parent = self._parent_of(commit_hash)
        return parent == ""

    # ---------- file IO ----------

    def read_html(self) -> str:
        if os.path.exists(self.html_file):
            with open(self.html_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def write_html(self, content: str) -> None:
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
        with open(src_path, "rb") as fsrc:
            with open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return os.path.join("imgs", os.path.basename(dst))

    def repo_ok(self) -> bool:
        return bool(self.repo_path) and os.path.isdir(
            os.path.join(self.repo_path, ".git"))

    # ---------- internal ----------

    def _ensure_identity(self):
        name = self._run_out("config", "user.name").strip()
        email = self._run_out("config", "user.email").strip()
        if not name:
            self._run("config", "user.name", "GitNote")
        if not email:
            self._run("config", "user.email", "note@git.local")

    def _run(self, *args) -> Tuple[int, str, str]:
        proc = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _run_out(self, *args) -> str:
        proc = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.stdout

    def _run_code(self, *args) -> int:
        proc = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode

    def _latest_hash(self) -> str:
        return self._run_out("rev-parse", "HEAD").strip()

    def _branches(self) -> List[str]:
        out = self._run_out("branch").strip()
        lines = [l.lstrip("* ").strip() for l in out.split("\n")]
        return [l for l in lines if l]

    def _current_branch(self) -> str:
        out = self._run_out("rev-parse", "--abbrev-ref", "HEAD").strip()
        if out == "HEAD":
            return ""
        return out

    def _parent_of(self, commit_hash: str) -> str:
        out = self._run_out("rev-parse", f"{commit_hash}^").strip()
        if not out or "unknown revision" in out.lower():
            return ""
        return out

    def _children_of(self, commit_hash: str, branch: str) -> List[str]:
        out = self._run_out("log", "--reverse", "--format=%H",
                            f"{commit_hash}..{branch}").strip()
        if not out:
            return []
        return [h for h in out.split("\n") if h]

    def _parse_refs(self, ref_str: str) -> List[str]:
        refs = []
        for part in ref_str.split(","):
            part = part.strip()
            if not part:
                continue
            if "->" in part:
                part = part.split("->")[-1].strip()
            part = part.replace("tag: ", "")
            refs.append(part)
        return refs

    def _fsck_repair_internal(self, folder: str) -> bool:
        proc = subprocess.run(
            ["git", "fsck", "--full"],
            cwd=folder, capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0

    def _assign_branches(self, nodes: Dict[str, CommitNode]):
        branches = self._branches()
        if not branches:
            return

        for n in nodes.values():
            n.lane = 0

        main_commits = set()
        out = self._run_out("log", "--reverse", "--format=%H", "main").strip()
        for h in out.split("\n"):
            h = h.strip()
            if h:
                main_commits.add(h)

        for h in main_commits:
            if h in nodes:
                nodes[h].lane = 0
                nodes[h].branch_name = "main"

        next_lane = 1
        for branch in branches:
            if branch == "main":
                continue

            branch_commits_all = set()
            out = self._run_out("log", "--reverse", "--format=%H", branch).strip()
            for h in out.split("\n"):
                h = h.strip()
                if h:
                    branch_commits_all.add(h)

            exclusive = branch_commits_all - main_commits
            if not exclusive:
                continue

            branch_hash = self._run_out("rev-parse", branch).strip()

            lane = next_lane
            next_lane += 1

            first_bh = None
            for h in exclusive:
                if h in nodes:
                    node = nodes[h]
                    if any(p in main_commits for p in node.parent_hashes):
                        first_bh = h

            for h in exclusive:
                if h in nodes:
                    nodes[h].lane = lane
                    nodes[h].branch_name = branch

            if first_bh and first_bh in nodes:
                nodes[first_bh].is_branch_start = True

            if branch_hash and branch_hash in nodes:
                nodes[branch_hash].refs.append(branch)
