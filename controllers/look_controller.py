"""
LOOK调度算法控制器
电梯在处理完同一方向的所有请求后转向，减少空转时间
"""
from typing import Dict, List, Set
import math

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent

class FloorType:
    """电梯运行目标楼层类型"""
    TARGET_FLOOR = "target_floor" # 需要停靠的楼层
    DESTINATION = "destination"  # 乘客有下梯需求的楼层


class LookController(ElevatorController):
    """LOOK调度算法控制器 - 处理同方向所有请求后转向"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", debug: bool = True):
        super().__init__(base_url, debug)
        # 分配参数，目前仅考虑
        self.alpha = 1.0  # 距离权重
        self.beta = None  # 队列长度权重
        self.gamma = 2.0  # 方向惩罚权重
        self.K = 10  # 同方向后方请求惩罚
        self.M = 100  # 反方向请求惩罚

        # 电梯调度
        self.max_floor = 0
        self.new_passengers: List[Dict] = []  # 记录新乘客信息，包括ID、所在楼层和目标楼层
        self.elevator_directions: Dict[int, Direction] = {}  # 记录电梯方向
        self.upward_passengers: Dict[int, List[tuple]] = {}  # 存储不同电梯的上行乘客信息(ID, origin, destination)
        self.downward_passengers: Dict[int, List[tuple]] = {}  # 存储不同电梯下行乘客信息(ID, origin, destination)
        self.elevator_destinations: List[Dict] = []  # 电梯运行计划
        self.elevator_status: Dict[int, Direction] = {}  # 电梯的需求处理状态

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化电梯到起始位置 - 从F0开始"""
        self.max_floor = floors[-1].floor if floors else 0

        self.beta = self.max_floor / len(elevators)  # 队列长度惩罚系数，楼层越高，电梯负担越重则惩罚越多

        if self.debug:
            print(f"初始化LOOK控制器: {len(elevators)}部电梯, {len(floors)}层楼")

        # LOOK算法初始化：所有电梯停在0层
        for i, elevator in enumerate(elevators):
            # 所有电梯都从底层开始
            target_floor = 0
            self.elevator_directions[elevator.id] = Direction.STOPPED  # 初始空闲
            self.upward_passengers[elevator.id] = []  # 上行信息初始化
            self.downward_passengers[elevator.id] = []  # 下行信息初始化
            self.elevator_destinations.append({FloorType.TARGET_FLOOR: set(), FloorType.DESTINATION: set()})  # 运行计划初始化
            self.elevator_status[elevator.id] = Direction.STOPPED  # 电梯需求处理状态初始化
            if self.debug:
                print(f"电梯 {elevator.id} 初始位置: 楼层 F{target_floor}, 状态: 空闲")

            elevator.go_to_floor(target_floor, immediate=True)

    def on_event_execute_start(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行前回调 - LOOK不做调度"""
        self.new_passengers = []  # 清空乘客列表

        if self.debug:
            print(f"Tick {tick}: 即将处理 {len(events)} 个事件 {[e.type.value for e in events]}")

            for elevator in elevators:
                elevator_status = self.elevator_status[elevator.id]
                direction = self.elevator_directions[elevator.id]
                target_floor = self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR]  # 获取当前运行计划的楼层
                destination = self.elevator_destinations[elevator.id][FloorType.DESTINATION]
                if elevator.is_full and destination:
                    target = min(destination) if elevator_status == Direction.UP else max(destination)
                elif (not elevator.is_full) and target_floor:
                    target = max(target_floor) if elevator_status == Direction.DOWN else min(target_floor)
                else:
                    target = elevator.current_floor

                print(f"\t电梯 {elevator.id}[{direction}] @ {elevator.current_floor} -> {target} | 乘客: {len(elevator.passengers)}")

            print()

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行后回调 - LOOK调度核心算法"""

        # 分配上个事件执行周期的新乘客
        self._assign_new_passengers(elevators)

        # 根据分配的乘客调度电梯
        for elevator in elevators:
            task_num = len(self.upward_passengers[elevator.id]) + len(self.downward_passengers[elevator.id])
            # 检查是否有乘客
            if task_num == 0:  # 没乘客电梯等候在原地
                elevator.go_to_floor(elevator.current_floor)
            else:  # 有乘客，开始调整电梯运行计划
                curr_floor = elevator.current_floor_float  # 当前楼层
                next_floor = math.floor(curr_floor)
                # 判断电梯当前运行方向，将需求加入电梯运行计划
                if self.elevator_directions[elevator.id] == Direction.STOPPED:  # 电梯空闲
                    # 找到距离当前楼层最近的需求楼层，更新电梯需求处理状态
                    if self.upward_passengers[elevator.id] and self.downward_passengers[elevator.id]:  # (ID, origin, destination) 上下行需求均不空
                        up_closest = min(self.upward_passengers[elevator.id], key=lambda x: abs(x[1] - curr_floor))
                        down_closest = min(self.downward_passengers[elevator.id], key=lambda x: abs(x[1] - curr_floor))
                        if abs(up_closest[1] - curr_floor) <= abs(down_closest[1] - curr_floor):
                            destination_floor = up_closest
                            self.elevator_status[elevator.id] = Direction.UP  # 调整电梯处理状态为处理上行需求
                        else:
                            destination_floor = down_closest
                            self.elevator_status[elevator.id] = Direction.DOWN
                    elif self.upward_passengers[elevator.id]:  # 上行需求不空
                        up_closest = min(self.upward_passengers[elevator.id], key=lambda x: abs(x[1] - curr_floor))
                        destination_floor = up_closest
                        self.elevator_status[elevator.id] = Direction.UP
                    elif self.downward_passengers[elevator.id]:  # 下行需求不空
                        down_closest = min(self.downward_passengers[elevator.id], key=lambda x: abs(x[1] - curr_floor))
                        destination_floor = down_closest
                        self.elevator_status[elevator.id] = Direction.DOWN
                    else:  # 需求已空
                        destination_floor = (None, None, None)
                        self.elevator_status[elevator.id] = Direction.STOPPED

                    if destination_floor == (None, None, None):  # 需求为空
                        pass
                    else:
                        # 调整电梯运行方向
                        self.elevator_directions[elevator.id] = Direction.UP if destination_floor[1] >= curr_floor else Direction.DOWN
                        # 将需求楼层添加到电梯运行计划
                        self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({destination_floor[1], destination_floor[2]})
                        self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(destination_floor[2])
                        next_floor = destination_floor[1]
                elif self.elevator_directions[elevator.id] == Direction.UP:  # 电梯上行
                    # 从上行需求中查询大于当前楼层的上行需求，如果有则将该需求加入电梯运行计划
                    filtered_up_requests = [t for t in self.upward_passengers[elevator.id] if t[1] > curr_floor]
                    if filtered_up_requests: # 当前楼层以上的上行需求非空
                        if self.elevator_status[elevator.id] != Direction.UP:  # 当前不是处理上行需求的状态
                            # 取消所有计划，优先处理上行需求
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].clear()
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].clear()
                        # 将所有上行需求加入运行计划
                        for up_request in filtered_up_requests:
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({up_request[1], up_request[2]})
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(up_request[2])
                        # 更改需求处理状态
                        self.elevator_status[elevator.id] = Direction.UP
                    else:  # 没有高于本楼层的上行需求
                        if self.elevator_status[elevator.id] != Direction.UP:  # 当前正在处理下行需求，那么将下行需求中最高的楼层加入运行计划
                            destination_floor = max(self.downward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({destination_floor[1], destination_floor[2]})
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(destination_floor[1])

                elif self.elevator_directions[elevator.id] == Direction.DOWN:
                    # 从下行需求列表中查询
                    filtered_down_requests = [t for t in self.downward_passengers[elevator.id] if t[1] < curr_floor]
                    if filtered_down_requests:  # 同理
                        if self.elevator_status[elevator.id] != Direction.DOWN:  # 当前不是处理下行需求的状态
                            # 清空所有计划，优先处理下行需求
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].clear()
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].clear()
                        # 将所有下行需求加入运行计划
                        for down_request in filtered_down_requests:
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({down_request[1], down_request[2]})
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(down_request[2])
                        self.elevator_status[elevator.id] = Direction.DOWN  # 更改需求处理状态
                    else:
                        if self.elevator_status[elevator.id] != Direction.DOWN:  # 当前正在处理上行需求
                            destination_floor = min(self.upward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({destination_floor[1], destination_floor[2]})
                            self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(destination_floor[1])

                # 维护电梯运行计划，判断是否前往处理另一种需求
                if self.elevator_directions[elevator.id] == Direction.UP:
                    # 上行状态，检查运行计划是否为空
                    if self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR]:  # 计划非空
                        pass
                    else:  # 当前运行计划已空
                        if self.downward_passengers[elevator.id]:  # 下行需求非空，找到下行需求中最高的楼层加入运行计划
                            destination_floor = max(self.downward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_status[elevator.id] = Direction.DOWN  # 更新需求处理状态
                        elif self.upward_passengers[elevator.id]: # 上行需求非空，找到上行需求中最低的楼层加入运行计划
                            destination_floor = min(self.upward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_status[elevator.id] = Direction.UP
                        else:  # 暂无任务，将电梯状态置为STOPPED
                            destination_floor = (None, None, None)
                            self.elevator_status[elevator.id] = Direction.STOPPED
                        # 更新电梯运行计划
                        self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({destination_floor[1], destination_floor[2]})
                        self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(destination_floor[2])
                elif self.elevator_directions[elevator.id] == Direction.DOWN:
                    # 下行状态，同理
                    if self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR]:  # 计划非空
                        pass
                    else:
                        if self.upward_passengers[elevator.id]:
                            destination_floor = min(self.upward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_status[elevator.id] = Direction.UP
                        elif self.downward_passengers[elevator.id]:
                            destination_floor = max(self.downward_passengers[elevator.id], key=lambda x: x[1])
                            self.elevator_status[elevator.id] = Direction.DOWN
                        else:
                            destination_floor = (None, None, None)
                            self.elevator_status[elevator.id] = Direction.STOPPED
                        # 更新电梯运行计划
                        self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].update({destination_floor[1], destination_floor[2]})
                        self.elevator_destinations[elevator.id][FloorType.DESTINATION].add(destination_floor[2])

                # 调度电梯楼层
                if self.elevator_status[elevator.id] == Direction.UP:  # 处理上行需求状态，直接去elevator_destinations中最小的楼层处
                    if elevator.is_full:  # 电梯已满，去往DESTINATION集合中最小的楼层
                        next_floor = min(self.elevator_destinations[elevator.id][FloorType.DESTINATION])
                        for fl in self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].copy():
                            if fl < next_floor:
                                self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].discard(fl)
                    else:  # 电梯未满，去往TARGET_FLOOR集合中最小的楼层
                        next_floor = min(self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR])
                    # 更新电梯运行方向
                    self.elevator_directions[elevator.id] = Direction.UP if next_floor >= curr_floor else Direction.DOWN
                elif self.elevator_status[elevator.id] == Direction.DOWN:  # 去最高楼层处
                    if elevator.is_full:
                        next_floor = max(self.elevator_destinations[elevator.id][FloorType.DESTINATION])
                        for fl in self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].copy():
                            if fl > next_floor:
                                self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].discard(fl)
                    else:
                        next_floor = max(self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR])
                    # 更新电梯运行方向
                    self.elevator_directions[elevator.id] = Direction.DOWN if next_floor <= curr_floor else Direction.UP
                else:  # 电梯状态为STOPPED
                    next_floor = next_floor  # 保持原地
                    self.elevator_directions[elevator.id] = Direction.STOPPED
                # 调度电梯去往下个目的地
                elevator.go_to_floor(next_floor)

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫电梯 - 更新新乘客信息，为分配乘客做准备_undone"""
        self.new_passengers.append({
            "passenger_id": passenger.id,
            "origin": floor.floor,
            "direction": Direction.UP if direction == "up" else Direction.DOWN,
            "destination": passenger.destination
        })

        if self.debug:
            print(f"乘客 {passenger.id} 在楼层 {floor.floor} 呼叫电梯前往 {passenger.destination} ({direction})")

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客登上电梯 - 打印信息"""
        if self.debug:
            print(f"乘客 {passenger.id} 进入电梯 {elevator.id} ({elevator.current_floor} -> {passenger.destination})")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下电梯 - 将乘客从对应电梯的上行和下行列表中移除"""
        if self.elevator_status[elevator.id] == Direction.UP:  # 电梯正在处理上行乘客需求
            for t in self.upward_passengers[elevator.id].copy():
                if t[0] == passenger.id:
                    self.upward_passengers[elevator.id].remove(t)
        else:
            for t in self.downward_passengers[elevator.id].copy():
                if t[0] == passenger.id:
                    self.downward_passengers[elevator.id].remove(t)

        if self.debug:
            print(f"乘客 {passenger.id} 在 {floor.floor} 层离开电梯 {elevator.id} ")

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠楼层 - 将当前楼层从电梯运行计划中移除"""
        self.elevator_destinations[elevator.id][FloorType.TARGET_FLOOR].discard(floor.floor)
        self.elevator_destinations[elevator.id][FloorType.DESTINATION].discard(floor.floor)

        if self.debug:
            print(f"[STOP] 电梯 {elevator.id} 停靠在楼层 {floor.floor}")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时 - 打印信息"""
        if self.debug:
            print(f"电梯 {elevator.id} 空闲")

    def on_elevator_move(self, elevator: ProxyElevator, from_position: dict, to_position: dict, direction: str,
                        status: str) -> None:
        """电梯移动时 - 可选实现"""
        if self.debug:
            print(f"电梯 {elevator.id} 移动: {from_position} -> {to_position}, 方向: {direction}, 状态: {status}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时 - 可选实现"""
        if self.debug:
            print(f"电梯 {elevator.id} 经过楼层 {floor.floor} (方向: {direction})")

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯接近楼层时 - 可选实现"""
        if self.debug:
            print(f"电梯 {elevator.id} 接近楼层 {floor.floor} (方向: {direction})")

    def _assign_new_passengers(self, elevators: List[ProxyElevator]) -> None:
        for passenger_info in self.new_passengers:
            passenger_id = passenger_info["passenger_id"]
            origin = passenger_info["origin"]
            direction = passenger_info["direction"]
            destination = passenger_info["destination"]
            best_elevator = None
            min_cost = float('inf')

            # 寻找代价最小的电梯
            for elevator in elevators:
                cost = self._calculate_assignment_cost(elevator, origin, direction)
                if cost < min_cost:
                    min_cost = cost
                    best_elevator = elevator

            # 将乘客按上行或下行需求分配给最佳电梯
            if direction == Direction.UP:
                self.upward_passengers[best_elevator.id].append((passenger_id, origin, destination))
            else:
                self.downward_passengers[best_elevator.id].append((passenger_id, origin, destination))

            if self.debug:
                print(f"乘客 {passenger_id} 分配给电梯 {best_elevator.id} (成本: {min_cost:.2f})")

    def _calculate_assignment_cost(self, elevator: ProxyElevator, origin: int, direction: Direction) -> float:
        distance_cost = self.alpha * abs(elevator.current_floor - origin)  # 距离惩罚
        queue_cost = self.beta * (len(self.upward_passengers[elevator.id]) + len(self.downward_passengers[elevator.id]))  # 队列惩罚

        return distance_cost + queue_cost
        # 忽略方向惩罚
        # elevator_dir = self.elevator_directions[elevator.id]
        #
        # if elevator_dir == Direction.STOPPED:
        #     direction_penalty = 0
        # elif elevator_dir == direction:
        #     if direction == Direction.UP:
        #         if origin >= elevator.current_floor:
        #             direction_penalty = 0
        #         else:
        #             direction_penalty = self.K
        #     else:
        #         if origin <= elevator.current_floor:
        #             direction_penalty = 0
        #         else:
        #             direction_penalty = self.K
        # else:
        #     direction_penalty = self.M

        # return distance_cost + queue_cost + self.gamma * direction_penalty


if __name__ == "__main__":
    # 创建并运行Bus控制器
    controller = LookController(debug=True)
    controller.start()
