import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLabel, QToolBar, QToolButton, QComboBox, QSpinBox, QInputDialog,
    QApplication
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor, QFont,
    QPolygonF, QBrush, QPainterPath
)
from PyQt5.QtCore import Qt, QRect, QPoint, QPointF, pyqtSignal, QTimer, QEvent

from path_helper import get_data_file_path


class ScreenshotWidget(QWidget):
    screenshot_taken = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.desktop = QApplication.primaryScreen()
        self.screen_rect = self.desktop.geometry()
        self.setGeometry(self.screen_rect)
        
        self.start_pos = None
        self.current_pos = None
        self.is_selecting = False
        self.selection_rect = None
        
        self.is_editing = False
        self.current_tool = 'select'
        self.current_color = QColor(255, 0, 0)
        self.current_width = 2
        self.annotations = []
        self.current_annotation = None
        self.undo_stack = []
        self.redo_stack = []
        
        self.base_screenshot = None
        self.toolbar = None
        self.toolbar_visible = False
        
        self.showFullScreen()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_editing:
                self._start_annotation(event.pos())
            else:
                self.start_pos = event.pos()
                self.current_pos = event.pos()
                self.is_selecting = True
                self.update()
        elif event.button() == Qt.RightButton:
            if self.is_editing:
                self.current_annotation = None
                self.update()
            else:
                self.close()
    
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.current_pos = event.pos()
            self.update()
        elif self.is_editing and self.current_annotation:
            self._update_annotation(event.pos())
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_editing and self.current_annotation:
                self._finish_annotation(event.pos())
            elif self.is_selecting:
                self.is_selecting = False
                rect = QRect(self.start_pos, event.pos()).normalized()
                
                if rect.width() < 5 or rect.height() < 5:
                    self.close()
                    return
                
                self.selection_rect = rect
                self._enter_edit_mode()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.is_editing:
                self._exit_edit_mode()
            else:
                self.close()
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            if event.modifiers() & Qt.ShiftModifier:
                self._redo()
            else:
                self._undo()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        if not self.is_editing:
            painter.fillRect(self.screen_rect, QColor(0, 0, 0, 180))
            
            if self.start_pos and self.current_pos:
                rect = QRect(self.start_pos, self.current_pos).normalized()
                
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.fillRect(rect, Qt.transparent)
                
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                pen = QPen(QColor(255, 0, 0, 255), 2)
                painter.setPen(pen)
                painter.drawRect(rect)
                
                size_text = f"{rect.width()} × {rect.height()}"
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 12))
                painter.drawText(
                    rect.bottomRight() + QPoint(10, 20),
                    size_text
                )
        else:
            if self.base_screenshot:
                painter.drawPixmap(self.selection_rect, self.base_screenshot)
            
            for annotation in self.annotations:
                self._draw_annotation(painter, annotation)
            
            if self.current_annotation:
                self._draw_annotation(painter, self.current_annotation)
    
    def _enter_edit_mode(self):
        self.is_editing = True
        
        screen = QApplication.primaryScreen()
        self.base_screenshot = screen.grabWindow(
            0,
            self.selection_rect.x(),
            self.selection_rect.y(),
            self.selection_rect.width(),
            self.selection_rect.height()
        )
        
        self._show_toolbar()
        self.update()
    
    def _exit_edit_mode(self):
        self.is_editing = False
        self._hide_toolbar()
        self.current_annotation = None
        self.update()
    
    def _show_toolbar(self):
        if self.toolbar:
            return
        
        self.toolbar = QToolBar(self)
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background: rgba(40, 40, 40, 240);
                border-radius: 8px;
                padding: 4px;
            }
            QToolButton {
                background: transparent;
                color: white;
                padding: 4px 8px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            QLabel {
                color: white;
                padding: 4px;
            }
        """)
        
        tools = [
            ('select', '▢', '选择'),
            ('line', '╱', '直线'),
            ('rect', '◻', '矩形'),
            ('arrow', '→', '箭头'),
            ('text', 'A', '文字'),
        ]
        
        self.tool_buttons = {}
        for tool_id, icon, tooltip in tools:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _, t=tool_id: self._set_tool(t))
            self.toolbar.addWidget(btn)
            self.tool_buttons[tool_id] = btn
        
        self.toolbar.addSeparator()
        
        color_label = QLabel("颜色:")
        self.toolbar.addWidget(color_label)
        
        self.color_combo = QComboBox()
        colors = [
            ("红色", QColor(255, 0, 0)),
            ("黄色", QColor(255, 255, 0)),
            ("绿色", QColor(0, 255, 0)),
            ("蓝色", QColor(0, 0, 255)),
            ("白色", QColor(255, 255, 255)),
            ("黑色", QColor(0, 0, 0)),
        ]
        for name, color in colors:
            self.color_combo.addItem(name, color)
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)
        self.toolbar.addWidget(self.color_combo)
        
        self.toolbar.addSeparator()
        
        width_label = QLabel("粗细:")
        self.toolbar.addWidget(width_label)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        self.toolbar.addWidget(self.width_spin)
        
        self.toolbar.addSeparator()
        
        undo_btn = QToolButton()
        undo_btn.setText("↶")
        undo_btn.setToolTip("撤销")
        undo_btn.clicked.connect(self._undo)
        self.toolbar.addWidget(undo_btn)
        
        redo_btn = QToolButton()
        redo_btn.setText("↷")
        redo_btn.setToolTip("重做")
        redo_btn.clicked.connect(self._redo)
        self.toolbar.addWidget(redo_btn)
        
        self.toolbar.addSeparator()
        
        save_btn = QToolButton()
        save_btn.setText("✓")
        save_btn.setToolTip("保存")
        save_btn.clicked.connect(self._save_screenshot)
        self.toolbar.addWidget(save_btn)
        
        cancel_btn = QToolButton()
        cancel_btn.setText("✕")
        cancel_btn.setToolTip("取消")
        cancel_btn.clicked.connect(self._exit_edit_mode)
        self.toolbar.addWidget(cancel_btn)
        
        toolbar_width = self.toolbar.sizeHint().width()
        x = (self.width() - toolbar_width) // 2
        self.toolbar.move(x, 10)
        self.toolbar.show()
        
        self._set_tool('select')
    
    def _hide_toolbar(self):
        if self.toolbar:
            self.toolbar.hide()
            self.toolbar.deleteLater()
            self.toolbar = None
    
    def _set_tool(self, tool_id):
        self.current_tool = tool_id
        
        for tool_id2, btn in self.tool_buttons.items():
            if tool_id2 == tool_id:
                btn.setStyleSheet("background: rgba(255, 255, 255, 0.3);")
            else:
                btn.setStyleSheet("")
    
    def _on_color_changed(self, index):
        self.current_color = self.color_combo.itemData(index)
    
    def _on_width_changed(self, value):
        self.current_width = value
    
    def _start_annotation(self, pos):
        if self.current_tool == 'select':
            return
        
        rel_pos = pos - self.selection_rect.topLeft()
        
        self.current_annotation = {
            'type': self.current_tool,
            'start': rel_pos,
            'end': rel_pos,
            'color': self.current_color,
            'width': self.current_width,
        }
        
        if self.current_tool == 'text':
            text, ok = QInputDialog.getText(
                self, "输入文字", "请输入标注文字:"
            )
            if ok and text:
                self.current_annotation['text'] = text
                self._finish_annotation(rel_pos)
            else:
                self.current_annotation = None
            return
    
    def _update_annotation(self, pos):
        if not self.current_annotation:
            return
        
        rel_pos = pos - self.selection_rect.topLeft()
        self.current_annotation['end'] = rel_pos
    
    def _finish_annotation(self, pos):
        if not self.current_annotation:
            return
        
        self.undo_stack.append(self.annotations.copy())
        self.redo_stack.clear()
        
        self.annotations.append(self.current_annotation.copy())
        self.current_annotation = None
        
        self.update()
    
    def _draw_annotation(self, painter, annotation):
        start = annotation['start']
        end = annotation['end']
        color = annotation['color']
        width = annotation['width']
        tool_type = annotation['type']
        
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        
        if tool_type == 'line':
            painter.drawLine(start, end)
        
        elif tool_type == 'rect':
            rect = QRect(start, end).normalized()
            painter.drawRect(rect)
        
        elif tool_type == 'arrow':
            self._draw_arrow(painter, start, end, color, width)
        
        elif tool_type == 'text':
            text = annotation.get('text', '')
            painter.setFont(QFont("Arial", 12))
            painter.setPen(color)
            painter.drawText(start, text)
    
    def _draw_arrow(self, painter, start, end, color, width):
        painter.drawLine(start, end)
        
        angle = 0.5
        arrow_size = 10 + width
        
        line = end - start
        length = (line.x() ** 2 + line.y() ** 2) ** 0.5
        if length == 0:
            return
        
        ux = line.x() / length
        uy = line.y() / length
        vx = -uy
        vy = ux
        
        p1 = end - QPointF(ux * arrow_size + vx * arrow_size * angle,
                           uy * arrow_size + vy * arrow_size * angle)
        p2 = end - QPointF(ux * arrow_size - vx * arrow_size * angle,
                           uy * arrow_size - vy * arrow_size * angle)
        
        path = QPainterPath()
        path.moveTo(end)
        path.lineTo(p1)
        path.lineTo(p2)
        path.closeSubpath()
        
        painter.setBrush(QBrush(color))
        painter.drawPath(path)
    
    def _undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.annotations.copy())
            self.annotations = self.undo_stack.pop()
            self.update()
    
    def _redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.annotations.copy())
            self.annotations = self.redo_stack.pop()
            self.update()
    
    def _save_screenshot(self):
        result_pixmap = QPixmap(self.base_screenshot)
        result_pixmap.fill(Qt.transparent)
        
        painter = QPainter(result_pixmap)
        painter.drawPixmap(0, 0, self.base_screenshot)
        
        for annotation in self.annotations:
            self._draw_annotation(painter, annotation)
        
        painter.end()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        imgs_dir = get_data_file_path("imgs")
        os.makedirs(imgs_dir, exist_ok=True)
        filepath = os.path.join(imgs_dir, filename)
        result_pixmap.save(filepath)
        
        self.screenshot_taken.emit(filepath)
        self.close()