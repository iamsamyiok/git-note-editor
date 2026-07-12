from dataclasses import dataclass, field
from typing import List


@dataclass
class CommitNode:
    hash: str
    parent_hashes: List[str] = field(default_factory=list)
    date: str = ""
    message: str = ""
    refs: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    branch_name: str = ""
    branch_color: str = ""
    is_root: bool = False
    is_branch_start: bool = False
    lane: int = 0
    row: int = 0
