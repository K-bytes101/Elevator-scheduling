"""
电梯调度可视化程序
使用PyQt6创建实时可视化界面
"""
import sys
import json
import requests
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QSpinBox, QGroupBox, QGridLayout, QFrame)
from PyQt6.QtCore import QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class SimulationData:
    """模拟数据类"""
    
    def __init__(self):
        self.elevators: List[Dict[str, Any]] = []
        self.floors: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
        self.tick = 0
        
    def update_elevators(self, elevators_data: List[Dict[str, Any]]) -> None:
        """更新电梯数据"""
        self.elevators = elevators_data
        
    def update_floors(self, floors_data: List[Dict[str, Any]]) -> None:
        """更新楼层数据"""
        self.floors = floors_data
        
    def update_events(self, events_data: List[Dict[str, Any]]) -> None:
        """更新事件数据"""
        self.events = events_data
        
    def update_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """更新指标数据"""
        self.metrics = metrics_data


class ElevatorWidget(QWidget):
    """电梯可视化组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = SimulationData()
        self.setMinimumSize(800, 600)
        self.setWindowTitle("电梯调度可视化")
        
    def paintEvent(self, event):
        """绘制电梯状态"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        if not self.data.floors or not self.data.elevators:
            painter.drawText(self.rect(), "等待数据...")
            return
        
        # 计算绘制参数
        floor_height = 40
        elevator_width = 60
        margin = 50
        floors_count = len(self.data.floors)
        
        # 绘制楼层
        for i, floor in enumerate(self.data.floors):
            y = margin + (floors_count - 1 - i) * floor_height
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.drawLine(margin, y, self.width() - margin, y)
            
            # 绘制楼层号
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(margin - 30, y + 5, f"F{floor['floor']}")
        
        # 绘制电梯
        elevators_count = len(self.data.elevators)
        for i, elevator in enumerate(self.data.elevators):
            # 计算电梯位置
            x = margin + 100 + i * (elevator_width + 20)
            
            # 计算电梯在楼层中的位置
            current_floor_float = elevator.get('current_floor_float', 0)
            floor_index = int(current_floor_float)
            floor_offset = current_floor_float - floor_index
            
            if floor_index < len(self.data.floors):
                y = margin + (floors_count - 1 - floor_index) * floor_height - floor_offset * floor_height
                
                # 绘制电梯
                painter.setBrush(QBrush(QColor(70, 130, 180)))
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.drawRect(x, y - floor_height + 10, elevator_width, floor_height - 10)
                
                # 绘制电梯ID
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                painter.drawText(x + 5, y - 5, f"E{elevator['id']}")
                
                # 绘制乘客数量
                passengers_count = len(elevator.get('passengers', []))
                if passengers_count > 0:
                    painter.setPen(QPen(QColor(255, 255, 0)))
                    painter.setFont(QFont("Arial", 8))
                    painter.drawText(x + 5, y - 20, f"👥{passengers_count}")
                
                # 绘制状态指示
                status = elevator.get('run_status', 'STOPPED')
                direction = elevator.get('target_floor_direction', 'STOPPED')
                
                if status == 'CONSTANT_SPEED':
                    if direction == 'UP':
                        painter.setPen(QPen(QColor(0, 255, 0), 3))
                        painter.drawText(x + elevator_width - 15, y - 5, "↑")
                    elif direction == 'DOWN':
                        painter.setPen(QPen(QColor(255, 0, 0), 3))
                        painter.drawText(x + elevator_width - 15, y - 5, "↓")
                elif status == 'START_UP':
                    painter.setPen(QPen(QColor(255, 165, 0), 3))
                    painter.drawText(x + elevator_width - 15, y - 5, "▲")
                elif status == 'START_DOWN':
                    painter.setPen(QPen(QColor(255, 165, 0), 3))
                    painter.drawText(x + elevator_width - 15, y - 5, "▼")
        
        # 绘制标题
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(10, 25, f"电梯调度可视化 - Tick: {self.data.tick}")
        
        # 绘制指标
        if self.data.metrics:
            metrics_text = f"完成: {self.data.metrics.get('completed_passengers', 0)}/{self.data.metrics.get('total_passengers', 0)}"
            painter.setFont(QFont("Arial", 10))
            painter.drawText(10, self.height() - 60, metrics_text)
            
            avg_wait = self.data.metrics.get('average_floor_wait_time', 0)
            painter.drawText(10, self.height() - 40, f"平均等待: {avg_wait:.1f}tick")
            
            p95_wait = self.data.metrics.get('p95_floor_wait_time', 0)
            painter.drawText(10, self.height() - 20, f"P95等待: {p95_wait:.1f}tick")


class DataFetcher(QThread):
    """数据获取线程"""
    
    data_updated = pyqtSignal(object)
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        super().__init__()
        self.base_url = base_url
        self.running = False
        
    def run(self):
        """运行数据获取循环"""
        self.running = True
        while self.running:
            try:
                # 获取状态数据
                state_response = requests.get(f"{self.base_url}/api/state", timeout=1)
                if state_response.status_code == 200:
                    state_data = state_response.json()
                    elevators_data = state_data.get('elevators', [])
                    floors_data = state_data.get('floors', [])
                    metrics_data = state_data.get('metrics', {})
                else:
                    elevators_data = []
                    floors_data = []
                    metrics_data = {}
                    
                    # 发送数据更新信号
                    data = SimulationData()
                    data.update_elevators(elevators_data)
                    data.update_floors(floors_data)
                    data.update_metrics(metrics_data)
                    data.tick = self.get_current_tick()
                    
                    self.data_updated.emit(data)
                    
            except Exception as e:
                print(f"数据获取错误: {e}")
                
            self.msleep(100)  # 100ms更新一次
    
    def get_current_tick(self) -> int:
        """获取当前tick"""
        try:
            response = requests.get(f"{self.base_url}/api/state", timeout=1)
            if response.status_code == 200:
                state_data = response.json()
                return state_data.get('tick', 0)
        except:
            pass
        return 0
    
    def stop(self):
        """停止数据获取"""
        self.running = False


class ElevatorVisualization(QMainWindow):
    """电梯可视化主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("电梯调度可视化系统")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        self.elevator_widget = ElevatorWidget()
        main_layout.addWidget(self.elevator_widget, 3)
        
        # 创建数据获取线程
        self.data_fetcher = DataFetcher()
        self.data_fetcher.data_updated.connect(self.update_data)
        
        # 启动数据获取
        self.data_fetcher.start()
        
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QGroupBox("控制面板")
        layout = QVBoxLayout(panel)
        
        # 连接状态
        self.status_label = QLabel("状态: 未连接")
        layout.addWidget(self.status_label)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接模拟器")
        self.connect_btn.clicked.connect(self.connect_simulator)
        layout.addWidget(self.connect_btn)
        
        # 步骤控制
        step_group = QGroupBox("步骤控制")
        step_layout = QGridLayout(step_group)
        
        self.step_count = QSpinBox()
        self.step_count.setRange(1, 100)
        self.step_count.setValue(1)
        step_layout.addWidget(QLabel("步数:"), 0, 0)
        step_layout.addWidget(self.step_count, 0, 1)
        
        self.step_btn = QPushButton("执行步骤")
        self.step_btn.clicked.connect(self.execute_step)
        step_layout.addWidget(self.step_btn, 0, 2)
        
        layout.addWidget(step_group)
        
        # 事件日志
        events_group = QGroupBox("事件日志")
        events_layout = QVBoxLayout(events_group)
        
        self.events_log = QTextEdit()
        self.events_log.setMaximumHeight(200)
        self.events_log.setReadOnly(True)
        events_layout.addWidget(self.events_log)
        
        layout.addWidget(events_group)
        
        # 指标显示
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.metrics_label = QLabel("等待数据...")
        metrics_layout.addWidget(self.metrics_label)
        
        layout.addWidget(metrics_group)
        
        return panel
    
    def connect_simulator(self):
        """连接模拟器"""
        try:
            response = requests.get("http://127.0.0.1:8000/api/state", timeout=2)
            if response.status_code == 200:
                self.status_label.setText("状态: 已连接")
                self.connect_btn.setText("已连接")
                self.connect_btn.setEnabled(False)
                self.log_event("成功连接到模拟器")
            else:
                self.status_label.setText("状态: 连接失败")
                self.log_event("连接失败: HTTP错误")
        except Exception as e:
            self.status_label.setText("状态: 连接失败")
            self.log_event(f"连接失败: {e}")
    
    def execute_step(self):
        """执行模拟步骤"""
        try:
            num_ticks = self.step_count.value()
            response = requests.post("http://127.0.0.1:8000/api/step", 
                                   json={"num_ticks": num_ticks}, timeout=2)
            if response.status_code == 200:
                events = response.json()
                self.log_event(f"执行了 {num_ticks} 个tick，产生 {len(events)} 个事件")
            else:
                self.log_event(f"执行步骤失败: HTTP错误")
        except Exception as e:
            self.log_event(f"执行步骤失败: {e}")
    
    def log_event(self, message: str):
        """记录事件"""
        self.events_log.append(f"[{self.get_current_time()}] {message}")
        # 限制日志长度
        if self.events_log.document().blockCount() > 100:
            cursor = self.events_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
    
    def get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    @pyqtSlot(object)
    def update_data(self, data: SimulationData):
        """更新数据"""
        self.elevator_widget.data = data
        self.elevator_widget.update()
        
        # 更新指标显示
        if data.metrics:
            metrics_text = f"""完成乘客: {data.metrics.get('completed_passengers', 0)}/{data.metrics.get('total_passengers', 0)}
平均楼层等待: {data.metrics.get('average_floor_wait_time', 0):.1f}tick
P95楼层等待: {data.metrics.get('p95_floor_wait_time', 0):.1f}tick
平均总等待: {data.metrics.get('average_arrival_wait_time', 0):.1f}tick
P95总等待: {data.metrics.get('p95_arrival_wait_time', 0):.1f}tick"""
            self.metrics_label.setText(metrics_text)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.data_fetcher.stop()
        self.data_fetcher.wait()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ElevatorVisualization()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
