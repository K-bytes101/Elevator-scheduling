"""
启动可视化程序的便捷脚本
"""
import sys
import subprocess
import os

def main():
    """启动可视化程序"""
    try:
        # 检查PyQt6是否安装
        try:
            import PyQt6
        except ImportError:
            print("错误: 未安装PyQt6")
            print("请运行: pip install PyQt6")
            sys.exit(1)
        
        # 启动可视化程序
        visualization_path = os.path.join("visualization", "elevator_visualization.py")
        subprocess.run([sys.executable, visualization_path])
        
    except Exception as e:
        print(f"启动可视化程序失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
