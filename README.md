# 电梯调度算法项目

这是一个基于Elevator Saga的电梯调度算法实现项目，包含Bus调度算法和实时可视化功能。

## 项目结构

```
Elevator-scheduling/
├── controllers/                    # 调度算法控制器
│   ├── __init__.py
│   ├── elevator_controller.py     # 电梯控制器基类
│   └── bus_controller.py          # Bus调度算法实现
├── visualization/                  # 可视化程序
│   ├── __init__.py
│   └── elevator_visualization.py  # PyQt6可视化界面
├── main.py                        # 主程序入口
├── run_visualization.py           # 可视化程序启动脚本
├── pyproject.toml                 # 项目配置
└── README.md                      # 项目说明
```

## 安装依赖

```bash
# 使用poetry安装依赖
poetry install

# 或者使用pip安装
pip install elevator-py pyqt6 requests
```

## 使用方法

### 1. 启动模拟器

首先需要启动Elevator Saga模拟器：

```bash
python -m elevator_saga.server.simulator
```

模拟器默认运行在 `http://127.0.0.1:8000`

### 2. 运行调度算法

运行Bus调度算法：

```bash
# 使用默认参数
python main.py

# 指定参数
python main.py --controller bus --url http://127.0.0.1:8000 --max-ticks 2000 --debug

# 查看帮助
python main.py --help
```

### 3. 启动可视化程序

在另一个终端中启动可视化程序：

```bash
# 使用便捷脚本
python run_visualization.py

# 或直接运行
python visualization/elevator_visualization.py
```

## Bus调度算法说明

Bus调度算法实现了简单的"公交车"式调度策略：

1. **固定路线**: 电梯按固定路线上下运行
2. **不响应呼叫**: 不主动响应乘客呼叫，按预定路线运行
3. **均匀分布**: 初始化时将电梯均匀分布到不同楼层
4. **循环运行**: 到达顶层后向下，到达底层后向上

### 算法特点

- **简单可靠**: 逻辑简单，易于理解和实现
- **基准算法**: 可作为其他算法的性能基准
- **固定模式**: 运行模式固定，便于测试和比较

## 可视化功能

可视化程序提供以下功能：

1. **实时显示**: 实时显示电梯位置、状态和乘客数量
2. **状态指示**: 用不同颜色和符号表示电梯运行状态
3. **性能指标**: 显示平均等待时间、P95等待时间等指标
4. **事件日志**: 记录模拟过程中的重要事件
5. **手动控制**: 可以手动执行模拟步骤

### 可视化说明

- **蓝色矩形**: 电梯
- **数字**: 电梯ID (E0, E1, ...)
- **👥数字**: 电梯内乘客数量
- **↑**: 向上运行 (绿色)
- **↓**: 向下运行 (红色)
- **▲/▼**: 加速/减速 (橙色)

## API接口

项目通过HTTP API与Elevator Saga模拟器通信：

- `GET /api/state` - 获取模拟器完整状态（包含电梯、楼层、指标信息）
- `POST /api/step` - 执行模拟步骤
- `POST /api/elevators/{id}/go_to_floor` - 控制电梯前往指定楼层

## 扩展开发

### 添加新的调度算法

1. 在 `controllers/` 目录下创建新的控制器文件
2. 继承 `ElevatorController` 基类
3. 实现必要的方法：
   - `on_init()` - 初始化
   - `on_passenger_call()` - 处理乘客呼叫
   - `on_elevator_stopped()` - 处理电梯停靠
   - `on_elevator_idle()` - 处理电梯空闲

### 示例：创建新算法

```python
from controllers.elevator_controller import ElevatorController, ProxyElevator, ProxyFloor, ProxyPassenger

class MyController(ElevatorController):
    def on_init(self, elevators, floors):
        # 初始化逻辑
        pass
    
    def on_passenger_call(self, passenger, floor, direction):
        # 处理乘客呼叫
        pass
    
    def on_elevator_stopped(self, elevator, floor):
        # 处理电梯停靠
        pass
    
    def on_elevator_idle(self, elevator):
        # 处理电梯空闲
        pass
```

## 性能指标

模拟器提供以下性能指标：

- **完成乘客数**: 已完成行程的乘客数量
- **总乘客数**: 总乘客数量
- **平均楼层等待时间**: 乘客在楼层等待的平均时间
- **P95楼层等待时间**: 95%乘客的楼层等待时间
- **平均总等待时间**: 乘客从到达到底达目的地的平均时间
- **P95总等待时间**: 95%乘客的总等待时间

## 注意事项

1. 确保模拟器已启动再运行调度算法
2. 可视化程序需要PyQt6支持
3. 调试模式下会输出详细的运行信息
4. 可以通过命令行参数调整模拟参数

## 故障排除

### 连接失败
- 检查模拟器是否已启动
- 确认URL地址正确
- 检查网络连接

### 可视化程序无法启动
- 确认已安装PyQt6: `pip install PyQt6`
- 检查Python版本 (需要3.11+)

### 性能问题
- 调整最大tick数
- 减少调试输出
- 检查系统资源使用情况
