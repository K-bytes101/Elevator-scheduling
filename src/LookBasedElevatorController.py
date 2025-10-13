#!/usr/bin/env python3
from typing import Dict, List, Set, Optional

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, EventType, SimulationEvent


class LookElevatorController(ElevatorController):
    """LOOK电梯调度算法控制器实现"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = True):
        super().__init__(server_url, debug)
        # 调度参数 (可调整)
        self.alpha = 1.0  # 距离权重
        self.beta = 0.5  # 队列长度权重
        self.gamma = 2.0  # 方向惩罚权重
        self.K = 10  # 同方向后方请求惩罚
        self.M = 100  # 反方向请求惩罚

        # 状态跟踪
        self.new_passengers: List[Dict] = []  # 新到达的乘客
        self.elevator_call_floors: Dict[int, Dict[int, int]] = {}  # 电梯ID -> {楼层: 等待乘客计数}
        self.elevator_destination_floors: Dict[int, Dict[int, int]] = {}  # 电梯ID -> {楼层: 目的地乘客计数}
        self.elevator_directions: Dict[int, Direction] = {}  # 电梯ID -> 当前方向
        self.elevator_targets: Dict[int, int] = {}  # 电梯ID -> 当前目标楼层
        self.max_floor = 0  # 最高楼层

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化控制器"""
        # 记录最高楼层
        self.max_floor = self.max_floor = len(floors) - 1

        # 初始化电梯状态
        for elevator in elevators:
            elevator_id = elevator.id
            self.elevator_call_floors[elevator_id] = {}
            self.elevator_destination_floors[elevator_id] = {}
            self.elevator_directions[elevator_id] = Direction.STOPPED
            self.elevator_targets[elevator_id] = elevator.current_floor

            # 设置初始方向
            if elevator.passengers:
                # 如果有乘客，根据第一个乘客的目的地设置方向
                first_passenger = elevator.passengers[0]
                if first_passenger.destination > elevator.current_floor:
                    self.elevator_directions[elevator_id] = Direction.UP
                else:
                    self.elevator_directions[elevator_id] = Direction.DOWN
                elevator.go_to_floor(first_passenger.destination)
                self.elevator_targets[elevator_id] = first_passenger.destination
            else:
                # 空闲电梯停在当前位置
                self.elevator_targets[elevator_id] = elevator.current_floor

    def on_event_execute_start(self, tick: int, events: List[SimulationEvent],
                               elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行前的回调"""
        # 重置新乘客列表
        self.new_passengers = []

        # 打印调试信息
        if self.debug:
            print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")
            for elevator in elevators:
                direction = self.elevator_directions[elevator.id].value
                target = self.elevator_targets[elevator.id]
                print(
                    f"\t电梯 {elevator.id}[{direction}] @ {elevator.current_floor} -> {target} | 乘客: {len(elevator.passengers)}")
            print()

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent],
                             elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行后的回调 - 核心调度逻辑"""
        # 分配新乘客
        self._assign_new_passengers(elevators)

        # 更新电梯目标
        for elevator in elevators:
            # 获取电梯需要服务的所有楼层
            requested_floors = self._get_requested_floors(elevator)

            if not requested_floors:
                # 没有请求，保持空闲
                self.elevator_directions[elevator.id] = Direction.STOPPED
                continue

            # 确定当前方向
            current_direction = self.elevator_directions[elevator.id]
            current_floor = elevator.current_floor

            # 如果电梯没有目标或已到达目标，选择新目标
            if (self.elevator_targets[elevator.id] is None or
                    self.elevator_targets[elevator.id] == current_floor):

                # 在当前方向上寻找下一个目标
                next_target = self._find_next_target(
                    current_floor, current_direction, requested_floors
                )

                if next_target is not None:
                    self.elevator_targets[elevator.id] = next_target
                    # 更新方向
                    direction = Direction.UP if next_target > current_floor else Direction.DOWN
                    self.elevator_directions[elevator.id] = direction

                    # 发送命令
                    elevator.go_to_floor(next_target)

                    if self.debug:
                        print(f"电梯 {elevator.id} 新目标: {next_target} ({direction.value})")

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫时的回调"""
        # 记录新乘客信息
        self.new_passengers.append({
            "passenger": passenger,
            "origin": floor.floor,
            "direction": Direction.UP if direction == "up" else Direction.DOWN
        })

        if self.debug:
            print(f"乘客 {passenger.id} 在 {floor.floor} 层呼叫 {direction} 电梯")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时的回调"""
        # 空闲时重新评估目标
        requested_floors = self._get_requested_floors(elevator)
        if requested_floors:
            next_target = self._find_next_target(
                elevator.current_floor,
                self.elevator_directions[elevator.id],
                requested_floors
            )
            if next_target is not None:
                self.elevator_targets[elevator.id] = next_target
                direction = Direction.UP if next_target > elevator.current_floor else Direction.DOWN
                self.elevator_directions[elevator.id] = direction
                elevator.go_to_floor(next_target)

                if self.debug:
                    print(f"空闲电梯 {elevator.id} 前往 {next_target} ({direction.value})")

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠时的回调"""

        if self.debug:
            print(f"电梯 {elevator.id} 停靠在 {floor.floor} 层")

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯时的回调"""
        # 乘客上梯后，移除呼叫楼层计数，添加目的地楼层计数
        origin = passenger.origin
        destination = passenger.destination

        # 更新呼叫楼层计数
        if origin in self.elevator_call_floors[elevator.id]:
            self.elevator_call_floors[elevator.id][origin] -= 1
            if self.elevator_call_floors[elevator.id][origin] <= 0:
                del self.elevator_call_floors[elevator.id][origin]

        # 更新目的地楼层计数
        if destination not in self.elevator_destination_floors[elevator.id]:
            self.elevator_destination_floors[elevator.id][destination] = 0
        self.elevator_destination_floors[elevator.id][destination] += 1

        if self.debug:
            print(f"乘客 {passenger.id} 进入电梯 {elevator.id} ({origin} -> {destination})")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下车时的回调"""
        # 乘客下车后，移除目的地楼层计数
        destination = passenger.destination

        if destination in self.elevator_destination_floors[elevator.id]:
            self.elevator_destination_floors[elevator.id][destination] -= 1
            if self.elevator_destination_floors[elevator.id][destination] <= 0:
                del self.elevator_destination_floors[elevator.id][destination]

        if self.debug:
            print(f"乘客 {passenger.id} 离开电梯 {elevator.id} 在 {floor.floor} 层")

    # 以下是需要实现的额外抽象方法
    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时的回调"""
        # 在LOOK算法中，我们通常不需要在此事件中执行操作
        # 但可以记录日志用于调试
        if self.debug:
            print(f"电梯 {elevator.id} 经过 {floor.floor} 层 ({direction})")

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达时的回调"""
        # 在LOOK算法中，我们通常不需要在此事件中执行操作
        # 但可以记录日志用于调试
        if self.debug:
            print(f"电梯 {elevator.id} 即将到达 {floor.floor} 层 ({direction})")

    def on_elevator_move(
            self, elevator: ProxyElevator, from_position: float, to_position: float, direction: str, status: str
    ) -> None:
        """电梯移动时的回调"""
        # 在LOOK算法中，我们通常不需要在此事件中执行操作
        # 但可以记录日志用于调试
        if self.debug:
            print(f"电梯 {elevator.id} 从 {from_position:.1f} 移动到 {to_position:.1f} ({direction}, {status})")

    # 以下是内部辅助方法
    def _assign_new_passengers(self, elevators: List[ProxyElevator]) -> None:
        """分配新乘客给电梯"""
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
                # 更新呼叫楼层计数
                if origin not in self.elevator_call_floors[best_elevator.id]:
                    self.elevator_call_floors[best_elevator.id][origin] = 0
                self.elevator_call_floors[best_elevator.id][origin] += 1

                if self.debug:
                    print(f"乘客 {passenger.id} 分配给电梯 {best_elevator.id} (成本: {min_cost:.2f})")

    def _calculate_assignment_cost(self, elevator: ProxyElevator,
                                   origin: int, direction: Direction) -> float:
        """计算将乘客分配给电梯的成本"""
        # 1. 距离成本
        distance_cost = self.alpha * abs(elevator.current_floor - origin)

        # 2. 队列长度成本
        queue_cost = self.beta * len(elevator.passengers)

        # 3. 方向惩罚
        direction_penalty = 0
        elevator_dir = self.elevator_directions[elevator.id]

        if elevator_dir == Direction.STOPPED:
            # 空闲电梯无惩罚
            direction_penalty = 0
        elif elevator_dir == direction:
            # 同方向
            if direction == Direction.UP:
                if origin >= elevator.current_floor:
                    # 在行进方向上
                    direction_penalty = 0
                else:
                    # 在行进方向后方
                    direction_penalty = self.K
            else:  # DOWN
                if origin <= elevator.current_floor:
                    # 在行进方向上
                    direction_penalty = 0
                else:
                    # 在行进方向后方
                    direction_penalty = self.K
        else:
            # 反方向
            direction_penalty = self.M

        return distance_cost + queue_cost + self.gamma * direction_penalty

    def _get_requested_floors(self, elevator: ProxyElevator) -> Set[int]:
        """获取电梯需要服务的所有楼层"""
        # 呼叫楼层 (等待接乘客)
        call_floors = set(self.elevator_call_floors[elevator.id].keys())

        # 目的地楼层 (等待下乘客)
        destination_floors = set(self.elevator_destination_floors[elevator.id].keys())

        return call_floors | destination_floors

    def _find_next_target(self, current_floor: int, direction: Direction,
                          requested_floors: Set[int]) -> Optional[int]:
        """根据LOOK算法寻找下一个目标楼层"""
        if not requested_floors:
            return None

        # 根据方向过滤楼层
        if direction == Direction.UP:
            # 优先处理上方的请求
            above_floors = [f for f in requested_floors if f > current_floor]
            if above_floors:
                return min(above_floors)  # 最近的楼层
            else:
                # 上方无请求，转向下方
                below_floors = [f for f in requested_floors if f < current_floor]
                if below_floors:
                    return max(below_floors)  # 最近的楼层（下方最大）
                else:
                    # 只有当前楼层？(理论上不会发生)
                    return current_floor if current_floor in requested_floors else None

        elif direction == Direction.DOWN:
            # 优先处理下方的请求
            below_floors = [f for f in requested_floors if f < current_floor]
            if below_floors:
                return max(below_floors)  # 最近的楼层
            else:
                # 下方无请求，转向上方
                above_floors = [f for f in requested_floors if f > current_floor]
                if above_floors:
                    return min(above_floors)  # 最近的楼层（上方最小）
                else:
                    # 只有当前楼层？(理论上不会发生)
                    return current_floor if current_floor in requested_floors else None

        else:  # STOPPED
            # 空闲状态，选择最近的请求
            return min(requested_floors, key=lambda f: abs(f - current_floor))


if __name__ == "__main__":
    # 创建并启动控制器
    controller = LookElevatorController(debug=True)
    controller.start()#!/usr/bin/env python3