"""
Bus调度算法控制器
实现简单的"公交车"式调度：电梯按固定路线上下运行
"""
from typing import List
import requests
from .elevator_controller import ElevatorController, ProxyElevator, ProxyFloor, ProxyPassenger


class BusController(ElevatorController):
    """Bus调度算法控制器 - 真正的公交车式调度"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000", debug: bool = True):
        super().__init__(base_url, debug)
        self.max_floor = 0
        self.elevator_directions = {}  # 记录每部电梯的运行方向
        
    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化电梯到起始位置 - Bus算法从底层开始"""
        self.max_floor = floors[-1].floor if floors else 0
        
        if self.debug:
            print(f"初始化Bus控制器: {len(elevators)}部电梯, {len(floors)}层楼")
        
        # Bus算法：所有电梯从底层(0层)开始，向上运行
        for i, elevator in enumerate(elevators):
            # 所有电梯都从底层开始
            target_floor = 0
            self.elevator_directions[elevator.id] = "up"  # 初始方向向上
            
            if self.debug:
                print(f"电梯 {elevator.id} 初始位置: 楼层 {target_floor}, 方向: 向上")
            
            elevator.go_to_floor(target_floor, immediate=True)
    
    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫电梯 - Bus算法不主动响应，按固定路线运行"""
        if self.debug:
            print(f"乘客 {passenger.id} 在楼层 {floor.floor} 呼叫电梯 ({direction}) - Bus算法记录，等待电梯经过")
        # Bus算法不主动响应乘客呼叫，电梯按固定路线运行
        # 乘客需要等待电梯按路线经过
    
    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠楼层时 - Bus算法继续按路线运行"""
        if self.debug:
            print(f"[STOP] 电梯 E{elevator.id} 停靠在楼层 F{floor.floor}")
        
        # Bus算法：继续按固定路线运行
        current_direction = self.elevator_directions.get(elevator.id, "up")
        current_floor = floor.floor
        
        # 特殊处理：在顶层和底层时，接纳所有方向的乘客
        if current_floor >= self.max_floor:
            # 到达顶层，改变方向向下，接纳所有下行乘客
            next_floor = current_floor - 1
            self.elevator_directions[elevator.id] = "down"
            if self.debug:
                print(f"电梯 {elevator.id} 到达顶层，改变方向向下，接纳所有下行乘客，前往楼层 {next_floor}")
        elif current_floor <= 0:
            # 到达底层，改变方向向上，接纳所有上行乘客
            next_floor = current_floor + 1
            self.elevator_directions[elevator.id] = "up"
            if self.debug:
                print(f"电梯 {elevator.id} 到达底层，改变方向向上，接纳所有上行乘客，前往楼层 {next_floor}")
        else:
            # 中间楼层，按当前方向继续
            if current_direction == "up":
                next_floor = current_floor + 1
                if self.debug:
                    print(f"电梯 {elevator.id} 继续向上，前往楼层 {next_floor}")
            else:  # down
                next_floor = current_floor - 1
                if self.debug:
                    print(f"电梯 {elevator.id} 继续向下，前往楼层 {next_floor}")
        
        # 设置下一个目标楼层
        elevator.go_to_floor(next_floor)
    
    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时 - Bus算法继续按路线运行"""
        if self.debug:
            print(f"电梯 {elevator.id} 空闲，继续按Bus路线运行")
        
        # Bus算法：空闲时也继续按路线运行
        current_direction = self.elevator_directions.get(elevator.id, "up")
        current_floor = elevator.current_floor
        
        # 特殊处理：在顶层和底层时，接纳所有方向的乘客
        if current_floor >= self.max_floor:
            next_floor = current_floor - 1
            self.elevator_directions[elevator.id] = "down"
            if self.debug:
                print(f"电梯 {elevator.id} 在顶层空闲，改变方向向下，前往楼层 {next_floor}")
        elif current_floor <= 0:
            next_floor = current_floor + 1
            self.elevator_directions[elevator.id] = "up"
            if self.debug:
                print(f"电梯 {elevator.id} 在底层空闲，改变方向向上，前往楼层 {next_floor}")
        else:
            # 中间楼层，按当前方向继续
            if current_direction == "up":
                next_floor = current_floor + 1
            else:  # down
                next_floor = current_floor - 1
        
        elevator.go_to_floor(next_floor)
    
    def on_elevator_move(self, elevator: ProxyElevator, from_position: dict, to_position: dict, direction: str, status: str) -> None:
        """电梯移动时 - 可选实现"""
        if self.debug:
            print(f"电梯 {elevator.id} 移动: {from_position} -> {to_position}, 方向: {direction}, 状态: {status}")
    
    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时 - Bus算法检查是否有乘客需要接载"""
        if self.debug:
            print(f"电梯 {elevator.id} 经过楼层 {floor.floor} (方向: {direction})")
        
        # 检查该楼层是否有乘客等待
        # 这里需要获取楼层状态，但当前API没有提供楼层队列信息
        # 简化处理：如果电梯没有目标，就停靠当前楼层
        if elevator.target_floor == elevator.current_floor:
            if self.debug:
                print(f"电梯 {elevator.id} 在楼层 {floor.floor} 停靠接载乘客")
            # 电梯已经停靠，不需要额外操作
    
    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯接近楼层时 - Bus算法检查是否需要停靠"""
        if self.debug:
            print(f"电梯 {elevator.id} 接近楼层 {floor.floor} (方向: {direction})")
        
        # Bus算法：检查该楼层是否有乘客等待
        try:
            state_response = requests.get(f"{self.base_url}/api/state")
            if state_response.status_code == 200:
                state_data = state_response.json()
                floors_data = state_data.get('floors', [])
                
                # 找到当前楼层
                current_floor_data = None
                for floor_data in floors_data:
                    if floor_data['floor'] == floor.floor:
                        current_floor_data = floor_data
                        break
                
                if current_floor_data:
                    # 检查是否有乘客等待
                    up_queue = current_floor_data.get('up_queue', [])
                    down_queue = current_floor_data.get('down_queue', [])
                    
                    should_stop = False
                    
                    # Bus算法：特殊处理顶层和底层
                    if floor.floor >= self.max_floor:
                        # 顶层：接纳所有下行乘客
                        if down_queue:
                            should_stop = True
                            if self.debug:
                                print(f"楼层 {floor.floor} 是顶层，有下行乘客，电梯停靠接载")
                        else:
                            if self.debug:
                                print(f"楼层 {floor.floor} 是顶层，没有下行乘客，电梯继续运行")
                    elif floor.floor <= 0:
                        # 底层：接纳所有上行乘客
                        if up_queue:
                            should_stop = True
                            if self.debug:
                                print(f"楼层 {floor.floor} 是底层，有上行乘客，电梯停靠接载")
                        else:
                            if self.debug:
                                print(f"楼层 {floor.floor} 是底层，没有上行乘客，电梯继续运行")
                    else:
                        # 中间楼层：只有同方向乘客才停靠
                        if direction == "up" and up_queue:
                            should_stop = True
                            if self.debug:
                                print(f"楼层 {floor.floor} 有上行乘客，电梯停靠接载")
                        elif direction == "down" and down_queue:
                            should_stop = True
                            if self.debug:
                                print(f"楼层 {floor.floor} 有下行乘客，电梯停靠接载")
                        else:
                            if self.debug:
                                print(f"楼层 {floor.floor} 没有同方向乘客，电梯继续运行")
                            
        except Exception as e:
            if self.debug:
                print(f"获取楼层状态失败: {e}")


if __name__ == "__main__":
    # 创建并运行Bus控制器
    controller = BusController(debug=True)
    controller.run_simulation(max_ticks=2000)
