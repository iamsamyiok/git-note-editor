from typing import Dict

from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QMenu, QAction, QWidget, QVBoxLayout, QPushButton,
    QHBoxLayout,
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QRadialGradient,
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QTimer,
)

from models import CommitNode

NODE_RADIUS = 12
ROOT_RADIUS = 20
BRANCH_START_RADIUS = 16
LANE_WIDTH = 220
ROW_HEIGHT = 90
LABEL_WIDTH = 180


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
        return QRectF(-r - 4, -r - 4, r * 2 + LABEL_WIDTH + 10, r * 2 + 20)

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
            painter.setPen(QPen(QColor(0, 0, 0, 80)))
            painter.setBrush(QBrush(QColor(255, 255, 255, 40)))
            painter.drawEllipse(QPointF(cx, cy), r + 2, r + 2)

        if self.commit.is_root:
            font = QFont("Microsoft YaHei", 8, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(QRectF(-r + 2, -6, r * 2 - 4, 12), Qt.AlignCenter, "根")

        label = self._format_label()
        if label:
            font = QFont("Microsoft YaHei", 8)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#222222")))
            text_rect = QRectF(r + 10, -20, LABEL_WIDTH, 40)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

    def _format_label(self) -> str:
        msg = self.commit.message or ""
        if "-" in msg:
            parts = msg.split("-", 1)
            date_str = parts[0].replace(".", "-")
            desc = parts[1].strip()
            if len(desc) > 30:
                desc = desc[:28] + ".."
            return f"{date_str}\n{desc}"
        return msg[:40]

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


class GraphView(QWidget):
    node_clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    graph_refresh_requested = pyqtSignal()
    new_commit_requested = pyqtSignal()
    new_branch_requested = pyqtSignal()
    new_branch_at_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 4, 4, 2)

        commit_btn = QPushButton("提交变更")
        commit_btn.setFixedHeight(28)
        commit_btn.clicked.connect(self.new_commit_requested.emit)
        btn_layout.addWidget(commit_btn)

        branch_btn = QPushButton("新建分支")
        branch_btn.setFixedHeight(28)
        branch_btn.clicked.connect(self.new_branch_requested.emit)
        btn_layout.addWidget(branch_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._view = QGraphicsView()
        self._scene = QGraphicsScene()
        self._view.setScene(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setDragMode(QGraphicsView.ScrollHandDrag)
        self._view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.mouseReleaseEvent = self._mouse_release
        self._view.wheelEvent = self._wheel_event
        self._view.contextMenuEvent = self._context_menu

        layout.addWidget(self._view)

        zoom_layout = QHBoxLayout()
        zoom_layout.setContentsMargins(4, 2, 4, 2)

        self._fit_btn = QPushButton("全览")
        self._fit_btn.setFixedSize(40, 24)
        self._fit_btn.setStyleSheet("font-size:10px;")
        self._fit_btn.clicked.connect(self._toggle_fit_view)
        zoom_layout.addWidget(self._fit_btn)

        self._current_node_btn = QPushButton("当前")
        self._current_node_btn.setFixedSize(40, 24)
        self._current_node_btn.setStyleSheet("font-size:10px;")
        self._current_node_btn.clicked.connect(self._go_to_current)
        zoom_layout.addWidget(self._current_node_btn)

        zoom_layout.addStretch()

        self.zoom_label = QPushButton("100%")
        self.zoom_label.setFixedSize(50, 24)
        self.zoom_label.setStyleSheet("font-size:11px;")
        self.zoom_label.clicked.connect(self._zoom_reset)
        zoom_layout.addWidget(self.zoom_label)

        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(28, 24)
        zoom_out_btn.setStyleSheet("font-size:16px; font-weight:bold;")
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(zoom_out_btn)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(28, 24)
        zoom_in_btn.setStyleSheet("font-size:16px; font-weight:bold;")
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(zoom_in_btn)

        layout.addLayout(zoom_layout)

        self._nodes: Dict[str, CommitNodeItem] = {}
        self._branch_labels = []
        self._current_hash = ""
        self._zoom_level = 1.0
        self._fit_mode = False
        self._saved_transform = None
        self._saved_scene_rect = None

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

        max_row = max((c.row for c in commits.values()), default=0)
        scene_rect = QRectF(
            0, 0,
            max_lane * LANE_WIDTH + 60,
            max_row * ROW_HEIGHT + ROW_HEIGHT + 40,
        )
        self._scene.setSceneRect(scene_rect)

        QTimer.singleShot(50, self._auto_center_current)

    def _auto_center_current(self):
        if self._current_hash and self._current_hash in self._nodes:
            self._view.centerOn(self._nodes[self._current_hash])

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
                    start_y = p1.y() + r
                    end_y = p2.y() - child_item.radius()
                    path.moveTo(p1.x(), start_y)
                    path.lineTo(p2.x(), end_y)
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
            if c.branch_name and c.branch_name not in seen:
                seen.add(c.branch_name)
                if h in self._nodes:
                    item = self._nodes[h]
                    pos = item.pos()
                    r = item.radius()

                    if c.branch_name == "main":
                        color = QColor("#4CAF50")
                    else:
                        color = QColor(c.branch_color or "#9E9E9E")
                    font = QFont("Microsoft YaHei", 9, QFont.Bold)

                    text = self._scene.addText(c.branch_name, font)
                    text.setDefaultTextColor(color)
                    text.setPos(pos.x() - 50, pos.y() - r - 22)

                    self._branch_labels.append(text)

    def _mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            item = self._view.itemAt(event.pos())
            if isinstance(item, CommitNodeItem):
                self._select_node(item.commit.hash)
                self.node_clicked.emit(item.commit.hash)
        QGraphicsView.mouseReleaseEvent(self._view, event)

    def _wheel_event(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.87
            self._view.scale(factor, factor)
            self._zoom_level *= factor
            self.zoom_label.setText(f"{int(self._zoom_level * 100)}%")
        else:
            QGraphicsView.wheelEvent(self._view, event)

    def _context_menu(self, event):
        item = self._view.itemAt(event.pos())
        if isinstance(item, CommitNodeItem):
            menu = QMenu(self)

            branch_action = QAction("在此新建分支", self)
            branch_action.triggered.connect(
                lambda: self.new_branch_at_requested.emit(item.commit.hash)
            )
            menu.addAction(branch_action)

            menu.addSeparator()

            del_action = QAction("删除本次提交", self)
            del_action.triggered.connect(
                lambda: self.delete_requested.emit(item.commit.hash)
            )
            menu.addAction(del_action)

            menu.addSeparator()

            refresh_action = QAction("刷新图谱", self)
            refresh_action.triggered.connect(
                self.graph_refresh_requested.emit
            )
            menu.addAction(refresh_action)

            menu.exec_(event.globalPos())

    def _select_node(self, hash_value: str):
        for h, item in self._nodes.items():
            item.set_selected(h == hash_value)

    def select_node(self, hash_value: str):
        self._select_node(hash_value)
        if hash_value in self._nodes:
            self._view.centerOn(self._nodes[hash_value])

    def _go_to_current(self):
        if self._current_hash and self._current_hash in self._nodes:
            self._view.centerOn(self._nodes[self._current_hash])

    def _toggle_fit_view(self):
        if not self._fit_mode:
            self._saved_transform = self._view.transform()
            self._saved_scene_rect = self._view.mapToScene(
                self._view.viewport().rect()
            ).boundingRect()
            self._view.fitInView(
                self._scene.sceneRect(), Qt.KeepAspectRatio
            )
            self._fit_mode = True
            self._fit_btn.setText("复原")
            self.zoom_label.setText("适应")
        else:
            if self._saved_transform is not None:
                self._view.setTransform(self._saved_transform)
            if self._saved_scene_rect is not None:
                self._view.centerOn(
                    self._saved_scene_rect.center()
                )
            self._fit_mode = False
            self._fit_btn.setText("全览")
            self.zoom_label.setText(f"{int(self._zoom_level * 100)}%")
            self._saved_transform = None
            self._saved_scene_rect = None

    def _zoom_in(self):
        self._fit_mode = False
        self._fit_btn.setText("全览")
        self._view.scale(1.2, 1.2)
        self._zoom_level *= 1.2
        self.zoom_label.setText(f"{int(self._zoom_level * 100)}%")

    def _zoom_out(self):
        self._fit_mode = False
        self._fit_btn.setText("全览")
        self._view.scale(0.83, 0.83)
        self._zoom_level *= 0.83
        self.zoom_label.setText(f"{int(self._zoom_level * 100)}%")

    def _zoom_reset(self):
        self._fit_mode = False
        self._fit_btn.setText("全览")
        self._view.resetTransform()
        self._zoom_level = 1.0
        self.zoom_label.setText("100%")
