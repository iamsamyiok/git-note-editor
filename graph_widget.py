import math
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QMenu, QAction, QMessageBox,
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QRadialGradient,
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal,
)

from models import CommitNode

BRANCH_COLORS = [
    "#2196F3", "#FF5722", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#795548", "#607D8B",
]

NODE_RADIUS = 12
ROOT_RADIUS = 20
BRANCH_START_RADIUS = 16
LANE_WIDTH = 200
ROW_HEIGHT = 80


class CommitNodeItem(QGraphicsItem):
    def __init__(self, commit: CommitNode):
        super().__init__()
        self.commit = commit
        self._hovered = False
        self._selected = False
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCursor(Qt.PointingHandCursor)

    def radius(self) -> float:
        if self.commit.is_root:
            return ROOT_RADIUS
        if self.commit.is_branch_start:
            return BRANCH_START_RADIUS
        return NODE_RADIUS

    def boundingRect(self) -> QRectF:
        r = self.radius()
        pad = 4
        return QRectF(-r - pad, -r - pad, (r + pad) * 2, (r + pad) * 2)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.radius()
        cx, cy = 0, 0

        if self.commit.is_root:
            painter.setPen(QPen(QColor("#E91E63"), 3))
            gradient = QRadialGradient(cx, cy, r)
            gradient.setColorAt(0, QColor("#FFCDD2"))
            gradient.setColorAt(1, QColor("#F44336"))
            painter.setBrush(QBrush(gradient))
        elif self.commit.is_branch_start:
            painter.setPen(QPen(QColor("#FF9800"), 2.5))
            gradient = QRadialGradient(cx, cy, r)
            gradient.setColorAt(0, QColor("#FFF3E0"))
            gradient.setColorAt(1, QColor("#FF9800"))
            painter.setBrush(QBrush(gradient))
        else:
            color = QColor(self.commit.branch_color or "#9E9E9E")
            pen = QPen(color, 2)
            if self._selected:
                pen.setWidth(3)
                pen.setColor(QColor("#FFD700"))
            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.white))

        painter.drawEllipse(QPointF(cx, cy), r, r)

        if self._selected:
            painter.setPen(QPen(QColor("#FFD700"), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r + 3, r + 3)

        if self._hovered:
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255, 40)))
            painter.drawEllipse(QPointF(cx, cy), r + 2, r + 2)

        if self.commit.is_root:
            font = QFont("Microsoft YaHei", 8, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            text_rect = QRectF(-r + 2, -6, r * 2 - 4, 12)
            painter.drawText(text_rect, Qt.AlignCenter, "根")

        label = self._short_label()
        if label:
            font = QFont("Microsoft YaHei", 7)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#333333")))
            text_rect = QRectF(r + 6, -14, 140, 28)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

    def _short_label(self) -> str:
        msg = self.commit.message
        parts = msg.split("-", 1)
        if len(parts) >= 2:
            return f"{parts[0]}\n{parts[1][:16]}"
        return msg[:20]

    def set_hovered(self, val: bool):
        self._hovered = val
        self.update()

    def set_selected(self, val: bool):
        self._selected = val
        self.update()

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._selected = True
            self.update()
        super().mousePressEvent(event)


class GraphView(QGraphicsView):
    node_clicked = pyqtSignal(str)
    node_right_clicked = pyqtSignal(str, QPointF)
    graph_refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nodes: Dict[str, CommitNodeItem] = {}
        self._connection_paths = []
        self._branch_labels = []
        self._current_hash = ""

    def set_commits(self, commits: Dict[str, CommitNode], current_hash: str):
        self._scene.clear()
        self._nodes.clear()
        self._branch_labels.clear()
        self._current_hash = current_hash

        if not commits:
            return

        max_lane = max((c.lane for c in commits.values()), default=0) + 1

        for h, c in commits.items():
            item = CommitNodeItem(c)
            x = c.lane * LANE_WIDTH + LANE_WIDTH // 2
            y = c.row * ROW_HEIGHT + ROW_HEIGHT // 2
            item.setPos(x, y)

            if h == current_hash:
                item.set_selected(True)

            self._scene.addItem(item)
            self._nodes[h] = item

        self._draw_connections(commits)
        self._draw_branch_labels(commits)

        scene_rect = QRectF(
            0, 0,
            max_lane * LANE_WIDTH + 40,
            max((c.row for c in commits.values()), default=0) * ROW_HEIGHT + ROW_HEIGHT + 40,
        )
        self._scene.setSceneRect(scene_rect)

        if current_hash and current_hash in self._nodes:
            self.centerOn(self._nodes[current_hash])

    def _draw_connections(self, commits: Dict[str, CommitNode]):
        for h, c in commits.items():
            for child_hash in c.children:
                if child_hash not in commits:
                    continue
                child = commits[child_hash]
                parent_item = self._nodes.get(h)
                child_item = self._nodes.get(child_hash)
                if not parent_item or not child_item:
                    continue

                p1 = parent_item.pos()
                p2 = child_item.pos()
                r = parent_item.radius()

                color = QColor(c.branch_color or "#9E9E9E")

                path = QPainterPath()
                if c.lane == child.lane:
                    path.moveTo(p1.x(), p1.y() + r)
                    path.lineTo(p2.x(), p2.y() - child_item.radius())
                    pen = QPen(color, 2)
                    self._scene.addPath(path, pen)
                else:
                    start_y = p1.y() + r
                    end_y = p2.y() - child_item.radius()
                    mid_y = (start_y + end_y) / 2

                    path.moveTo(p1.x(), start_y)
                    path.cubicTo(
                        p1.x(), mid_y,
                        p2.x(), mid_y,
                        p2.x(), end_y,
                    )
                    pen = QPen(color, 2)
                    self._scene.addPath(path, pen)

    def _draw_branch_labels(self, commits: Dict[str, CommitNode]):
        seen = set()
        for h, c in commits.items():
            if c.branch_name and c.branch_name not in seen and c.branch_name != "main":
                seen.add(c.branch_name)
                if h in self._nodes:
                    item = self._nodes[h]
                    pos = item.pos()
                    r = item.radius()

                    color = QColor(c.branch_color or "#9E9E9E")
                    font = QFont("Microsoft YaHei", 9, QFont.Bold)

                    text = self._scene.addText(c.branch_name, font)
                    text.setDefaultTextColor(color)
                    text.setPos(pos.x() - 50, pos.y() - r - 22)

                    self._branch_labels.append(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.pos())
            if isinstance(item, CommitNodeItem):
                self.node_right_clicked.emit(
                    item.commit.hash,
                    self.mapToScene(event.pos()),
                )
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, CommitNodeItem):
                self._select_node(item.commit.hash)
                self.node_clicked.emit(item.commit.hash)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.87
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def _select_node(self, hash_value: str):
        for h, item in self._nodes.items():
            item.set_selected(h == hash_value)

    def select_node(self, hash_value: str):
        self._select_node(hash_value)
        if hash_value in self._nodes:
            self.centerOn(self._nodes[hash_value])

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, CommitNodeItem):
            menu = QMenu(self)

            del_action = QAction("删除本次提交", self)
            del_action.triggered.connect(
                lambda: self.node_right_clicked.emit(
                    item.commit.hash, QPointF()
                )
            )
            menu.addAction(del_action)

            refresh_action = QAction("刷新图谱", self)
            refresh_action.triggered.connect(
                self.graph_refresh_requested.emit
            )
            menu.addAction(refresh_action)

            menu.exec_(event.globalPos())
