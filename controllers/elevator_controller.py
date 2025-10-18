"""
电梯控制器基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests
import json


class ProxyElevator:
    """电梯代理类，用于与模拟器通信"""
    
    def __init__(self, elevator_id: int, api_client):
        self.id = elevator_id
        self.api_client = api_client
        self._state = {}
        
    def go_to_floor(self, floor: int, immediate: bool = False) -> None:
        """让电梯前往指定楼层"""
        url = f"{self.api_client.base_url}/api/elevators/{self.id}/go_to_floor"
        data = {"floor": floor, "immediate": immediate}
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"Error sending elevator {self.id} to floor {floor}: {response.text}")
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """更新电梯状态"""
        self._state.update(state)
    
    @property
    def current_floor(self) -> int:
        """当前楼层"""
        return self._state.get('current_floor', 0)
    
    @property
    def current_floor_float(self) -> float:
        """当前楼层（浮点数）"""
        return self._state.get('current_floor_float', 0.0)
    
    @property
    def target_floor(self) -> int:
        """目标楼层"""
        return self._state.get('target_floor', 0)
    
    @property
    def target_floor_direction(self) -> str:
        """目标楼层方向"""
        return self._state.get('target_floor_direction', 'STOPPED')
    
    @property
    def run_status(self) -> str:
        """运行状态"""
        return self._state.get('run_status', 'STOPPED')
    
    @property
    def passengers(self) -> List[int]:
        """乘客列表"""
        return self._state.get('passengers', [])
    
    @property
    def last_tick_direction(self) -> str:
        """上一tick的方向"""
        return self._state.get('last_tick_direction', 'STOPPED')


class ProxyFloor:
    """楼层代理类"""
    
    def __init__(self, floor_number: int):
        self.floor = floor_number


class ProxyPassenger:
    """乘客代理类"""
    
    def __init__(self, passenger_id: int, api_client):
        self.id = passenger_id
        self.api_client = api_client


class SimulationEvent:
    """模拟事件"""
    
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data


class ElevatorController(ABC):
    """电梯控制器基类"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000", debug: bool = False):
        self.base_url = base_url
        self.debug = debug
        self.api_client = self
        self.elevators: List[ProxyElevator] = []
        self.floors: List[ProxyFloor] = []
        
    def connect(self) -> bool:
        """连接到模拟器"""
        try:
            response = requests.get(f"{self.base_url}/api/state")
            return response.status_code == 200
        except:
            return False
    
    def get_elevators(self) -> List[ProxyElevator]:
        """获取电梯列表"""
        try:
            response = requests.get(f"{self.base_url}/api/state")
            if response.status_code == 200:
                state_data = response.json()
                elevators_data = state_data.get('elevators', [])
                self.elevators = []
                for elevator_data in elevators_data:
                    elevator = ProxyElevator(elevator_data['id'], self)
                    elevator.update_state(elevator_data)
                    self.elevators.append(elevator)
                return self.elevators
        except Exception as e:
            if self.debug:
                print(f"Error getting elevators: {e}")
        return []
    
    def get_floors(self) -> List[ProxyFloor]:
        """获取楼层列表"""
        try:
            response = requests.get(f"{self.base_url}/api/state")
            if response.status_code == 200:
                state_data = response.json()
                floors_data = state_data.get('floors', [])
                self.floors = []
                for floor_data in floors_data:
                    floor = ProxyFloor(floor_data['floor'])
                    self.floors.append(floor)
                return self.floors
        except Exception as e:
            if self.debug:
                print(f"Error getting floors: {e}")
        return []
    
    def step(self, num_ticks: int = 1) -> List[SimulationEvent]:
        """执行模拟步骤"""
        try:
            response = requests.post(f"{self.base_url}/api/step", json={"num_ticks": num_ticks})
            if response.status_code == 200:
                response_data = response.json()
                events_data = response_data.get('events', [])
                events = []
                for event_data in events_data:
                    event = SimulationEvent(event_data['type'], event_data['data'])
                    events.append(event)
                return events
        except Exception as e:
            if self.debug:
                print(f"Error stepping simulation: {e}")
        return []
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            response = requests.get(f"{self.base_url}/api/state")
            if response.status_code == 200:
                state_data = response.json()
                return state_data.get('metrics', {})
        except Exception as e:
            if self.debug:
                print(f"Error getting metrics: {e}")
        return {}
    
    def run_simulation(self, max_ticks: int = 10000, wait_for_visualization: bool = False, visualization_wait_time: int = 5, tick_delay: float = 0.0) -> None:
        """运行模拟"""
        if not self.connect():
            print("无法连接到模拟器")
            return
        
        # 初始化
        self.elevators = self.get_elevators()
        self.floors = self.get_floors()
        
        if not self.elevators or not self.floors:
            print("无法获取电梯或楼层信息")
            return
        
        # 调用初始化方法
        self.on_init(self.elevators, self.floors)
        
        # 等待可视化程序启动
        if wait_for_visualization:
            print(f"等待可视化程序启动 ({visualization_wait_time}秒)...")
            import time
            time.sleep(visualization_wait_time)
            print("开始运行调度算法...")
        
        tick = 0
        while tick < max_ticks:
            # 获取事件
            events = self.step(1)
            tick += 1
            
            if self.debug and events:
                print(f"Tick {tick}: Processing {len(events)} events")
            
            # 处理事件
            self._execute_events(events)
            
            # 更新电梯状态
            self.elevators = self.get_elevators()
            
            # 添加延迟以便可视化
            if tick_delay > 0:
                import time
                time.sleep(tick_delay)
            
            # 检查是否完成
            metrics = self.get_metrics()
            if metrics.get('completed_passengers', 0) > 0 and metrics.get('total_passengers', 0) == metrics.get('completed_passengers', 0):
                print(f"模拟完成，总tick数: {tick}")
                break
        
        # 输出最终指标
        final_metrics = self.get_metrics()
        print("最终性能指标:")
        print(f"完成乘客数: {final_metrics.get('completed_passengers', 0)}")
        print(f"总乘客数: {final_metrics.get('total_passengers', 0)}")
        print(f"平均楼层等待时间: {final_metrics.get('average_floor_wait_time', 0):.2f}")
        print(f"P95楼层等待时间: {final_metrics.get('p95_floor_wait_time', 0):.2f}")
        print(f"平均总等待时间: {final_metrics.get('average_arrival_wait_time', 0):.2f}")
        print(f"P95总等待时间: {final_metrics.get('p95_arrival_wait_time', 0):.2f}")
    
    def _execute_events(self, events: List[SimulationEvent]) -> None:
        """处理事件"""
        for event in events:
            if event.type == "up_button_pressed":
                passenger_id = event.data["passenger"]
                floor_num = event.data["floor"]
                floor = self.floors[floor_num] if floor_num < len(self.floors) else None
                passenger = ProxyPassenger(passenger_id, self.api_client)
                self.on_passenger_call(passenger, floor, "up")
                
            elif event.type == "down_button_pressed":
                passenger_id = event.data["passenger"]
                floor_num = event.data["floor"]
                floor = self.floors[floor_num] if floor_num < len(self.floors) else None
                passenger = ProxyPassenger(passenger_id, self.api_client)
                self.on_passenger_call(passenger, floor, "down")
                
            elif event.type == "stopped_at_floor":
                elevator_id = event.data["elevator"]
                floor_num = event.data["floor"]
                elevator = self.elevators[elevator_id] if elevator_id < len(self.elevators) else None
                floor = self.floors[floor_num] if floor_num < len(self.floors) else None
                if elevator and floor:
                    self.on_elevator_stopped(elevator, floor)
                    
            elif event.type == "idle":
                elevator_id = event.data["elevator"]
                elevator = self.elevators[elevator_id] if elevator_id < len(self.elevators) else None
                if elevator:
                    self.on_elevator_idle(elevator)
                    
            elif event.type == "elevator_move":
                elevator_id = event.data["elevator"]
                elevator = self.elevators[elevator_id] if elevator_id < len(self.elevators) else None
                if elevator:
                    from_position = event.data["from_position"]
                    to_position = event.data["to_position"]
                    direction = event.data["direction"]
                    status = event.data["status"]
                    self.on_elevator_move(elevator, from_position, to_position, direction, status)
                    
            elif event.type == "passing_floor":
                elevator_id = event.data["elevator"]
                floor_num = event.data["floor"]
                direction = event.data["direction"]
                elevator = self.elevators[elevator_id] if elevator_id < len(self.elevators) else None
                floor = self.floors[floor_num] if floor_num < len(self.floors) else None
                if elevator and floor:
                    self.on_elevator_passing_floor(elevator, floor, direction)
                    
            elif event.type == "elevator_approaching":
                elevator_id = event.data["elevator"]
                floor_num = event.data["floor"]
                direction = event.data["direction"]
                elevator = self.elevators[elevator_id] if elevator_id < len(self.elevators) else None
                floor = self.floors[floor_num] if floor_num < len(self.floors) else None
                if elevator and floor:
                    self.on_elevator_approaching(elevator, floor, direction)
    
    @abstractmethod
    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化时调用"""
        pass
    
    @abstractmethod
    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫电梯时调用"""
        pass
    
    @abstractmethod
    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠楼层时调用"""
        pass
    
    @abstractmethod
    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时调用"""
        pass
    
    def on_elevator_move(self, elevator: ProxyElevator, from_position: Dict, to_position: Dict, direction: str, status: str) -> None:
        """电梯移动时调用（可选实现）"""
        pass
    
    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时调用（可选实现）"""
        pass
    
    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯接近楼层时调用（可选实现）"""
        pass
