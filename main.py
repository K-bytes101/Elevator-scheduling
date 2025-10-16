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
    parser.add_argument("--debug", "-d", action="store_true",
                       help="启用调试模式")
    
    args = parser.parse_args()
    
    print(f"启动电梯调度算法: {args.controller}")
    print(f"模拟器URL: {args.url}")
    print(f"最大tick数: {args.max_ticks}")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    print("-" * 50)
    
    # 根据参数创建对应的控制器
    if args.controller == "bus":
        controller = BusController(base_url=args.url, debug=args.debug)
    else:
        print(f"未知的调度算法: {args.controller}")
        sys.exit(1)
    
    # 运行模拟
    try:
        controller.run_simulation(max_ticks=args.max_ticks)
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
