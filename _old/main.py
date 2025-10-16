import threading
from controllers.look_controller import LookElevatorController
from visualization.elevator_visualization import ElevatorVisualization

if __name__ == "__main__":
    # 选择控制器（可以切换为其他控制器）
    controller = LookElevatorController(debug=True)

    # 创建可视化
    visualization = ElevatorVisualization(controller, max_floor=10)
    controller.visualization = visualization

    # 启动模拟线程
    simulation_thread = threading.Thread(target=controller.start, daemon=True)
    simulation_thread.start()

    # 启动 PyQt 主循环
    visualization.show()