from typing import Dict, List
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QTreeWidget, QTreeWidgetItem, QTextEdit, QScrollBar, QFrame
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator
from elevator_saga.core.models import Direction

class ElevatorVisualization(QObject):
    """电梯模拟可视化界面（使用 PyQt5 实现）"""
    update_ui_signal = pyqtSignal()
    log_signal = pyqtSignal(str)

    def __init__(self, controller: ElevatorController, max_floor: int = 10,
                 ui_interval_ms: int = 100, anim_smoothness: float = 0.25):
        super().__init__()
        self.controller = controller
        self.max_floor = max_floor
        self.ui_interval_ms = ui_interval_ms
        self.anim_smoothness = max(0.05, min(anim_smoothness, 1.0))
        self.floor_height = 50
        self.elevator_width = 64
        self.elevator_height = 40
        self.elevator_spacing = 18
        self.left_margin = 140
        self.right_margin = 60
        self.canvas_default_width = 1000
        self.bg_color = QColor("#f7f7f8")
        self.floor_line_color = QColor("#d0d0d0")
        self.text_color = QColor("#222222")
        self.elevator_up_color = QColor("#4CAF50")
        self.elevator_down_color = QColor("#F44336")
        self.elevator_stop_color = QColor("#2196F3")
        self.waiting_passenger_color = QColor("#FF9800")
        self.inside_passenger_color = QColor("#9E9E9E")
        self.elevator_border_color = QColor("#333333")
        self.font_small = QFont("Arial", 10)
        self.font_bold = QFont("Arial", 10, QFont.Bold)
        self.elevator_positions: Dict[int, int] = {}
        self._positions_initialized = False
        self.visual_y: Dict[int, float] = {}
        self.app = QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle("电梯调度模拟")
        self.window.resize(1200, 900)
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.canvas = QWidget()
        self.canvas.setMinimumHeight(max(300, (self.max_floor + 1) * self.floor_height + 40))
        self.canvas.paintEvent = self._paint_canvas
        self.canvas.resizeEvent = self._on_canvas_resize
        shaft_frame = QFrame()
        shaft_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        shaft_layout = QVBoxLayout(shaft_frame)
        shaft_layout.addWidget(QLabel("电梯井视图"))
        shaft_layout.addWidget(self.canvas)
        main_layout.addWidget(shaft_frame)
        self._create_status_panel(main_layout)
        self._create_control_panel(main_layout)
        self._create_log_panel(main_layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(self.ui_interval_ms)
        self.update_ui_signal.connect(self.update_ui)
        self.log_signal.connect(self._log_event_slot)

    def show(self):
        self.window.show()
        sys.exit(self.app.exec_())

    def _paint_canvas(self, event):
        painter = QPainter(self.canvas)
        painter.fillRect(self.canvas.rect(), self.bg_color)
        self._draw_floor_lines(painter)
        self._draw_waiting_passengers(painter)
        self._draw_elevators(painter)

    def _on_canvas_resize(self, event):
        shaft_width = self.canvas.width()
        self.canvas_default_width = max(self.canvas_default_width, shaft_width)
        elevators = getattr(self.controller, "elevators", [])
        if elevators:
            self._init_elevator_positions(elevators)
        self.canvas.update()

    def _get_shaft_width(self) -> int:
        return max(50, self.canvas.width())

    def _draw_floor_lines(self, painter: QPainter):
        shaft_width = self._get_shaft_width()
        pen = QPen(self.floor_line_color, 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setFont(self.font_small)
        for floor in range(self.max_floor + 1):
            y = (self.max_floor - floor) * self.floor_height + 20
            painter.drawLine(self.left_margin, y, shaft_width - self.right_margin, y)
            painter.setPen(self.text_color)
            painter.drawText(0, y - 10, self.left_margin - 18, 20, Qt.AlignRight, f"F{floor}")
            painter.setPen(pen)

    def _init_elevator_positions(self, elevators: List[ProxyElevator]):
        if not elevators:
            return
        elevs = sorted(elevators, key=lambda e: e.id)
        shaft_width = self._get_shaft_width()
        usable_width = max(300, shaft_width - self.left_margin - self.right_margin)
        num = len(elevs)
        spacing = self.elevator_spacing
        total = num * self.elevator_width + (num - 1) * spacing
        if total > usable_width:
            spacing = max(4, (usable_width - num * self.elevator_width) // max(1, num - 1))
        start_x = self.left_margin + (usable_width - total) // 2
        new_positions = {}
        for i, e in enumerate(elevs):
            x = start_x + i * (self.elevator_width + spacing)
            new_positions[e.id] = x
        self.elevator_positions = new_positions
        self._positions_initialized = True

    def _get_elevator_floor(self, elevator: ProxyElevator) -> float:
        if hasattr(elevator, "position"):
            try:
                return float(elevator.position)
            except Exception:
                pass
        if hasattr(elevator, "current_floor"):
            try:
                return float(elevator.current_floor)
            except Exception:
                pass
        return 0.0

    def update_ui(self):
        try:
            elevators = getattr(self.controller, "elevators", [])
            self.max_floor = getattr(self.controller, "max_floor", self.max_floor)
            if elevators:
                self._ensure_positions_match_elevators(elevators)
            self._update_status_panel(elevators)
            self.canvas.update()
        except Exception as e:
            print(f"UI 更新错误: {e}")
            self.log_signal.emit(f"UI 更新错误: {e}")

    def _ensure_positions_match_elevators(self, elevators: List[ProxyElevator]):
        ids_now = set(self.elevator_positions.keys())
        ids_new = set(e.id for e in elevators)
        if ids_now != ids_new or not self._positions_initialized:
            self._init_elevator_positions(elevators)

    def _draw_waiting_passengers(self, painter: QPainter):
        waiting_by_floor: Dict[int, int] = {}
        for e_calls in getattr(self.controller, "elevator_call_floors", {}).values():
            for floor, cnt in e_calls.items():
                waiting_by_floor[floor] = waiting_by_floor.get(floor, 0) + cnt
        r = 6
        spacing = 2 * r + 4
        max_inline = 10
        start_x = 12
        brush = QBrush(self.waiting_passenger_color)
        pen = QPen(self.elevator_border_color, 1)
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.setFont(self.font_small)
        for floor, cnt in waiting_by_floor.items():
            if cnt <= 0:
                continue
            y = (self.max_floor - floor) * self.floor_height + 20
            display = min(cnt, max_inline)
            for i in range(display):
                cx = start_x + i * spacing
                painter.drawEllipse(cx - r, y - r, 2 * r, 2 * r)
            if cnt > max_inline:
                painter.setPen(self.text_color)
                painter.drawText(start_x + max_inline * spacing + 8, y - 10, 50, 20, Qt.AlignLeft, f"x{cnt}")

    def _draw_elevators(self, painter: QPainter):
        elevators = getattr(self.controller, "elevators", [])
        for e in sorted(elevators, key=lambda x: x.id):
            x = self.elevator_positions.get(e.id, self.left_margin)
            cur_floor = self._get_elevator_floor(e)
            target_y = (self.max_floor - cur_floor) * self.floor_height + 20
            if e.id not in self.visual_y:
                self.visual_y[e.id] = float(target_y)
            cur_vis_y = self.visual_y[e.id]
            new_vis_y = cur_vis_y + (target_y - cur_vis_y) * self.anim_smoothness
            self.visual_y[e.id] = new_vis_y
            left = x
            right = x + self.elevator_width
            top = int(new_vis_y - self.elevator_height // 2)
            bottom = int(new_vis_y + self.elevator_height // 2)
            direction = self.controller.elevator_directions.get(e.id, Direction.STOPPED)
            if direction == Direction.UP:
                color = self.elevator_up_color
            elif direction == Direction.DOWN:
                color = self.elevator_down_color
            else:
                color = self.elevator_stop_color
            brush = QBrush(color)
            pen = QPen(self.elevator_border_color, 2)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawRect(left, top, self.elevator_width, self.elevator_height)
            painter.setFont(self.font_bold)
            painter.setPen(QColor("white"))
            painter.drawText(left, top, self.elevator_width, 20, Qt.AlignCenter, f"E{e.id}")
            passenger_count = len(getattr(e, "passengers", []))
            painter.drawText(left, bottom - 20, self.elevator_width, 20, Qt.AlignCenter, str(passenger_count))
            inside_cnt = passenger_count
            if inside_cnt > 0:
                r = 6
                spacing = 2 * r + 2
                cols = max(1, (self.elevator_width - 8) // spacing)
                rows = (inside_cnt + cols - 1) // cols
                total_w = cols * spacing
                total_h = rows * spacing
                sx = left + (self.elevator_width - total_w) // 2 + r
                sy = top + (self.elevator_height - total_h) // 2 + r
                brush = QBrush(self.inside_passenger_color)
                pen = QPen(self.elevator_border_color, 1)
                painter.setBrush(brush)
                painter.setPen(pen)
                for i in range(min(inside_cnt, cols * rows)):
                    col = i % cols
                    row = i // cols
                    cx = sx + col * spacing
                    cy = sy + row * spacing
                    painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
                if inside_cnt > cols * rows:
                    painter.setFont(QFont("Arial", 12, QFont.Bold))
                    painter.setPen(self.text_color)
                    painter.drawText(left, top, self.elevator_width, self.elevator_height, Qt.AlignCenter, f"{inside_cnt}")

    def _create_status_panel(self, main_layout: QVBoxLayout):
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        status_layout = QVBoxLayout(status_frame)
        status_layout.addWidget(QLabel("电梯状态"))
        self.status_tree = QTreeWidget()
        self.status_tree.setColumnCount(6)
        self.status_tree.setHeaderLabels(["ID", "位置", "方向", "目标", "乘客数", "目的地"])
        status_layout.addWidget(self.status_tree)
        main_layout.addWidget(status_frame)

    def _update_status_panel(self, elevators: List[ProxyElevator]):
        self.status_tree.clear()
        for elevator in elevators:
            elevator_id = str(elevator.id)
            position = f"{self._get_elevator_floor(elevator):.1f}"
            direction = self.controller.elevator_directions.get(elevator.id, Direction.STOPPED).name
            target = str(self.controller.elevator_targets.get(elevator.id, "N/A"))
            passengers = str(len(getattr(elevator, "passengers", [])))
            dest_floors = self.controller.elevator_destination_floors.get(elevator.id, {})
            destinations = ", ".join(str(f) for f in dest_floors.keys()) if dest_floors else "无"
            item = QTreeWidgetItem([elevator_id, position, direction, target, passengers, destinations])
            self.status_tree.addTopLevelItem(item)

    def _create_control_panel(self, main_layout: QVBoxLayout):
        control_frame = QWidget()
        control_layout = QHBoxLayout(control_frame)
        speed_up_btn = QPushButton("加速")
        speed_up_btn.clicked.connect(self.speed_up)
        control_layout.addWidget(speed_up_btn)
        speed_down_btn = QPushButton("减速")
        speed_down_btn.clicked.connect(self.speed_down)
        control_layout.addWidget(speed_down_btn)
        toggle_pause_btn = QPushButton("暂停/继续")
        toggle_pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(toggle_pause_btn)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_simulation)
        control_layout.addWidget(reset_btn)
        param_frame = QFrame()
        param_layout = QVBoxLayout(param_frame)
        param_layout.addWidget(QLabel("视觉参数"))
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("刷新 (ms):"))
        self.ui_interval_slider = QSlider(Qt.Horizontal)
        self.ui_interval_slider.setRange(30, 500)
        self.ui_interval_slider.setValue(self.ui_interval_ms)
        self.ui_interval_slider.valueChanged.connect(self._on_ui_interval_change)
        interval_layout.addWidget(self.ui_interval_slider)
        param_layout.addLayout(interval_layout)
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("平滑度:"))
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(5, 100)
        self.smooth_slider.setValue(int(self.anim_smoothness * 100))
        self.smooth_slider.valueChanged.connect(self._on_smooth_change)
        smooth_layout.addWidget(self.smooth_slider)
        param_layout.addLayout(smooth_layout)
        control_layout.addWidget(param_frame)
        main_layout.addWidget(control_frame)

    def _on_ui_interval_change(self, value):
        self.ui_interval_ms = value
        self.timer.setInterval(self.ui_interval_ms)

    def _on_smooth_change(self, value):
        self.anim_smoothness = value / 100.0

    def _create_log_panel(self, main_layout: QVBoxLayout):
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        log_layout = QVBoxLayout(log_frame)
        log_layout.addWidget(QLabel("事件日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_frame)

    def _log_event_slot(self, message: str):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def log_event(self, message: str):
        self.log_signal.emit(message)

    def speed_up(self):
        if hasattr(self.controller, "speed_up"):
            self.controller.speed_up()
        self.log_event("模拟加速")

    def speed_down(self):
        if hasattr(self.controller, "speed_down"):
            self.controller.speed_down()
        self.log_event("模拟减速")

    def toggle_pause(self):
        if hasattr(self.controller, "toggle_pause"):
            self.controller.toggle_pause()
        self.log_event("模拟暂停/继续")

    def reset_simulation(self):
        if hasattr(self.controller, "reset"):
            self.controller.reset()
        self.log_event("模拟已重置")