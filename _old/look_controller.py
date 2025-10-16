# 可用版本 1.0
from typing import Dict, List, Set, Optional
import time
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction

class LookElevatorController(ElevatorController):
    """LOOK电梯调度算法控制器实现"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False):
        super().__init__(server_url, debug)
        # 调度参数
        self.alpha = 1.0  # 距离权重
        self.beta = 0.5  # 队列长度权重
        self.gamma = 2.0  # 方向惩罚权重
        self.K = 10  # 同方向后方请求惩罚
        self.M = 100  # 反方向请求惩罚
        # 状态跟踪
        self.new_passengers: List[Dict] = []
        self.elevator_call_floors: Dict[int, Dict[int, int]] = {}
        self.elevator_destination_floors: Dict[int, Dict[int, int]] = {}
        self.elevator_directions: Dict[int, Direction] = {}
        self.elevator_targets: Dict[int, int] = {}
        self.max_floor = 0
        self.visualization = None
        # 模拟速度控制
        self.simulation_delay = 0.5
        self.paused = False

    def speed_up(self):
        """加速模拟（减少延迟）"""
        self.simulation_delay = max(0.01, self.simulation_delay / 2)
        if self.debug:
            print(f"模拟延迟调整为: {self.simulation_delay:.2f} 秒")
            if self.visualization:
                self.visualization.log_event(f"模拟延迟调整为: {self.simulation_delay:.2f} 秒")

    def speed_down(self):
        """减速模拟（增加延迟）"""
        self.simulation_delay *= 2
        if self.debug:
            print(f"模拟延迟调整为: {self.simulation_delay:.2f} 秒")
            if self.visualization:
                self.visualization.log_event(f"模拟延迟调整为: {self.simulation_delay:.2f} 秒")

    def toggle_pause(self):
        """切换暂停状态"""
        self.paused = not self.paused
        if self.debug:
            print(f"模拟已{'暂停' if self.paused else '继续'}")
            if self.visualization:
                self.visualization.log_event(f"模拟已{'暂停' if self.paused else '继续'}")

    def reset(self):
        """重置模拟"""
        try:
            self._api_client.reset()
        except AttributeError:
            self.new_passengers = []
            self.elevator_call_floors = {}
            self.elevator_destination_floors = {}
            self.elevator_directions = {}
            self.elevator_targets = {}
            if self.debug:
                print("模拟内部状态已重置（API 重置未实现）")
                if self.visualization:
                    self.visualization.log_event("模拟内部状态已重置（API 重置未实现）")

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self.max_floor = len(floors) - 1
        for elevator in elevators:
            elevator_id = elevator.id
            self.elevator_call_floors[elevator_id] = {}
            self.elevator_destination_floors[elevator_id] = {}
            self.elevator_directions[elevator_id] = Direction.STOPPED
            self.elevator_targets[elevator_id] = elevator.current_floor
        if self.visualization:
            self.visualization.max_floor = self.max_floor
            try:
                self.visualization._init_elevator_positions(elevators)
                self.visualization.update_ui_signal.emit()
            except Exception as e:
                print(f"初始化错误: {e}")
                if self.visualization:
                    self.visualization.log_event(f"初始化错误: {e}")

    def on_event_execute_start(self, tick: int, events: List['SimulationEvent'],
                              elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self.new_passengers = []
        if self.debug:
            debug_msg = f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}"
            print(debug_msg)
            if self.visualization:
                self.visualization.log_event(debug_msg)
            for elevator in elevators:
                direction = self.elevator_directions.get(elevator.id, Direction.STOPPED).value
                target = self.elevator_targets.get(elevator.id, elevator.current_floor)
                elevator_msg = f"\t电梯 {elevator.id}[{direction}] @ {elevator.current_floor} -> {target} | 乘客: {len(elevator.passengers)}"
                print(elevator_msg)
                if self.visualization:
                    self.visualization.log_event(elevator_msg)
            print()

    def on_event_execute_end(self, tick: int, events: List['SimulationEvent'],
                            elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self._assign_new_passengers(elevators)
        for elevator in elevators:
            requested_floors = self._get_requested_floors(elevator)
            if not requested_floors:
                self.elevator_directions[elevator.id] = Direction.STOPPED
                continue
            current_direction = self.elevator_directions[elevator.id]
            current_floor = elevator.current_floor
            if (self.elevator_targets[elevator.id] is None or
                    self.elevator_targets[elevator.id] == current_floor):
                next_target = self._find_next_target(
                    current_floor, current_direction, requested_floors
                )
                if next_target is not None:
                    self.elevator_targets[elevator.id] = next_target
                    direction = Direction.UP if next_target > current_floor else Direction.DOWN
                    self.elevator_directions[elevator.id] = direction
                    elevator.go_to_floor(next_target)
                    if self.debug:
                        debug_msg = f"电梯 {elevator.id} 新目标: {next_target} ({direction.value})"
                        print(debug_msg)
                        if self.visualization:
                            self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()
        while self.paused:
            time.sleep(0.1)
        time.sleep(self.simulation_delay)

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        try:
            self.new_passengers.append({
                "passenger": passenger,
                "origin": floor.floor,
                "direction": Direction.UP if direction == "up" else Direction.DOWN
            })
            if self.debug:
                debug_msg = f"乘客 {passenger._passenger_id} 在 F{floor.floor} 呼叫 {direction} 电梯"
                print(debug_msg)
                if self.visualization:
                    self.visualization.log_event(debug_msg)
            if self.visualization:
                self.visualization.update_ui_signal.emit()
        except Exception as e:
            print(f"乘客呼叫错误: {e}")
            if self.visualization:
                self.visualization.log_event(f"乘客呼叫错误: {e}")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        requested_floors = self._get_requested_floors(elevator)
        if requested_floors:
            next_target = self._find_next_target(
                elevator.current_floor, self.elevator_directions[elevator.id], requested_floors
            )
            if next_target is not None:
                self.elevator_targets[elevator.id] = next_target
                direction = Direction.UP if next_target > elevator.current_floor else Direction.DOWN
                self.elevator_directions[elevator.id] = direction
                elevator.go_to_floor(next_target)
                if self.debug:
                    debug_msg = f"空闲电梯 {elevator.id} 前往 {next_target} ({direction.value})"
                    print(debug_msg)
                    if self.visualization:
                        self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        if self.debug:
            debug_msg = f"电梯 {elevator.id} 停靠在 {floor.floor} 层"
            print(debug_msg)
            if self.visualization:
                self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        try:
            origin = elevator.current_floor
            destination = passenger.destination
            if origin in self.elevator_call_floors[elevator.id]:
                self.elevator_call_floors[elevator.id][origin] -= 1
                if self.elevator_call_floors[elevator.id][origin] <= 0:
                    del self.elevator_call_floors[elevator.id][origin]
            if destination not in self.elevator_destination_floors[elevator.id]:
                self.elevator_destination_floors[elevator.id][destination] = 0
            self.elevator_destination_floors[elevator.id][destination] += 1
            if self.debug:
                debug_msg = f"乘客 {passenger._passenger_id} 进入电梯 {elevator.id} ({origin} -> {destination})"
                print(debug_msg)
                if self.visualization:
                    self.visualization.log_event(debug_msg)
            if self.visualization:
                self.visualization.update_ui_signal.emit()
        except ValueError as e:
            if self.debug:
                print(f"乘客 {passenger._passenger_id} 上电梯错误: {e}")
                if self.visualization:
                    self.visualization.log_event(f"乘客上电梯错误 (ID: {passenger._passenger_id}): {e}")
        except Exception as e:
            print(f"上电梯回调意外错误: {e}")
            if self.visualization:
                self.visualization.log_event(f"上电梯回调意外错误: {e}")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        try:
            destination = floor.floor
            if destination in self.elevator_destination_floors[elevator.id]:
                self.elevator_destination_floors[elevator.id][destination] -= 1
                if self.elevator_destination_floors[elevator.id][destination] <= 0:
                    del self.elevator_destination_floors[elevator.id][destination]
            if self.debug:
                debug_msg = f"乘客 {passenger._passenger_id} 离开电梯 {elevator.id} 在 {floor.floor} 层"
                print(debug_msg)
                if self.visualization:
                    self.visualization.log_event(debug_msg)
            if self.visualization:
                self.visualization.update_ui_signal.emit()
        except Exception as e:
            print(f"下电梯错误: {e}")
            if self.visualization:
                self.visualization.log_event(f"下电梯错误: {e}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        if self.debug:
            debug_msg = f"电梯 {elevator.id} 经过 {floor.floor} 层 ({direction})"
            print(debug_msg)
            if self.visualization:
                self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        if self.debug:
            debug_msg = f"电梯 {elevator.id} 即将到达 {floor.floor} 层 ({direction})"
            print(debug_msg)
            if self.visualization:
                self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()

    def on_elevator_move(self, elevator: ProxyElevator, from_position: float,
                        to_position: float, direction: str, status: str) -> None:
        if self.debug:
            debug_msg = f"电梯 {elevator.id} 从 {from_position:.1f} 移动到 {to_position:.1f} ({direction}, {status})"
            print(debug_msg)
            if self.visualization:
                self.visualization.log_event(debug_msg)
        if self.visualization:
            self.visualization.update_ui_signal.emit()

    def _assign_new_passengers(self, elevators: List[ProxyElevator]) -> None:
        for passenger_info in self.new_passengers:
            passenger = passenger_info["passenger"]
            origin = passenger_info["origin"]
            direction = passenger_info["direction"]
            best_elevator = None
            min_cost = float('inf')
            for elevator in elevators:
                cost = self._calculate_assignment_cost(elevator, origin, direction)
                if cost < min_cost:
                    min_cost = cost
                    best_elevator = elevator
            if best_elevator:
                if origin not in self.elevator_call_floors[best_elevator.id]:
                    self.elevator_call_floors[best_elevator.id][origin] = 0
                self.elevator_call_floors[best_elevator.id][origin] += 1
                if self.debug:
                    debug_msg = f"乘客 {passenger._passenger_id} 分配给电梯 {best_elevator.id} (成本: {min_cost:.2f})"
                    print(debug_msg)
                    if self.visualization:
                        self.visualization.log_event(debug_msg)

    def _calculate_assignment_cost(self, elevator: ProxyElevator, origin: int, direction: Direction) -> float:
        distance_cost = self.alpha * abs(elevator.current_floor - origin)
        queue_cost = self.beta * len(elevator.passengers)
        direction_penalty = 0
        elevator_dir = self.elevator_directions[elevator.id]
        if elevator_dir == Direction.STOPPED:
            direction_penalty = 0
        elif elevator_dir == direction:
            if direction == Direction.UP:
                if origin >= elevator.current_floor:
                    direction_penalty = 0
                else:
                    direction_penalty = self.K
            else:
                if origin <= elevator.current_floor:
                    direction_penalty = 0
                else:
                    direction_penalty = self.K
        else:
            direction_penalty = self.M
        return distance_cost + queue_cost + self.gamma * direction_penalty

    def _get_requested_floors(self, elevator: ProxyElevator) -> Set[int]:
        call_floors = set(self.elevator_call_floors.get(elevator.id, {}).keys())
        destination_floors = set(self.elevator_destination_floors.get(elevator.id, {}).keys())
        return call_floors | destination_floors

    def _find_next_target(self, current_floor: int, direction: Direction,
                          requested_floors: Set[int]) -> Optional[int]:
        if not requested_floors:
            return None
        if direction == Direction.UP:
            above_floors = [f for f in requested_floors if f > current_floor]
            if above_floors:
                return min(above_floors)
            else:
                below_floors = [f for f in requested_floors if f < current_floor]
                if below_floors:
                    return max(below_floors)
                else:
                    return current_floor if current_floor in requested_floors else None
        elif direction == Direction.DOWN:
            below_floors = [f for f in requested_floors if f < current_floor]
            if below_floors:
                return max(below_floors)
            else:
                above_floors = [f for f in requested_floors if f > current_floor]
                if above_floors:
                    return min(above_floors)
                else:
                    return current_floor if current_floor in requested_floors else None
        else:
            return min(requested_floors, key=lambda f: abs(f - current_floor))