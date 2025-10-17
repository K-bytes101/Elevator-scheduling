"""
电梯调度算法主程序入口
"""
import sys
import argparse
from controllers.bus_controller import BusController


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="电梯调度算法")
    parser.add_argument("--controller", "-c", default="bus",
                       choices=["bus"],
                       help="选择调度算法 (默认: bus)")
    parser.add_argument("--url", "-u", default="http://127.0.0.1:8000",
                       help="模拟器URL (默认: http://127.0.0.1:8000)")
    parser.add_argument("--max-ticks", "-t", type=int, default=2000,
                       help="最大tick数 (默认: 2000)")
    parser.add_argument("--debug", action="store_true",
                       help="启用调试模式")
    parser.add_argument("--wait-visualization", "-w", action="store_true",
                       help="等待可视化程序启动")
    parser.add_argument("--visualization-wait-time", type=float, default=2.5,
                       help="等待可视化程序的时间(秒) (默认: 2.5)")
    parser.add_argument("--tick-delay", "-d", type=float, default=0,
                       help="每个tick之间的延迟时间(秒) (默认: 0)")

    args = parser.parse_args()

    print(f"启动电梯调度算法: {args.controller}")
    print(f"模拟器URL: {args.url}")
    print(f"最大tick数: {args.max_ticks}")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    print(f"等待可视化: {'开启' if args.wait_visualization else '关闭'}")
    if args.wait_visualization:
        print(f"等待时间: {args.visualization_wait_time}秒")
    print(f"Tick延迟: {args.tick_delay}秒")
    print("-" * 50)

    # 根据参数创建对应的控制器
    if args.controller == "bus":
        controller = BusController(base_url=args.url, debug=args.debug)
    else:
        print(f"未知的调度算法: {args.controller}")
        sys.exit(1)

    # 运行模拟
    try:
        controller.run_simulation(
            max_ticks=args.max_ticks,
            wait_for_visualization=args.wait_visualization,
            visualization_wait_time=args.visualization_wait_time,
            tick_delay=args.tick_delay
        )
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
if __name__ == "__main__":
    main()