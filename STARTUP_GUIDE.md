# 电梯调度算法启动指南

## 启动脚本说明

本项目提供了一个功能完整的启动脚本，方便一键运行整个电梯调度系统。

### start.bat - 完整功能启动脚本

**功能**: 一键启动模拟器、调度算法和可视化程序，支持参数配置

**使用方法**:
```bash
# 使用默认配置（推荐）
start.bat

# 指定调度算法
start.bat --controller bus

# 指定最大tick数
start.bat --max-ticks 1000

# 禁用调试模式
start.bat --no-debug

# 不等待可视化程序
start.bat --no-wait

# 自定义等待时间
start.bat --wait-time 10

# 设置延迟以便可视化演示
start.bat --tick-delay 1.0

# 组合使用
start.bat --controller bus --max-ticks 1000 --no-debug --no-wait --tick-delay 0.5

# 显示帮助
start.bat --help
```

**参数说明**:
- `--controller [算法]`: 指定调度算法 (默认: bus)
- `--max-ticks [数量]`: 指定最大tick数 (默认: 2000)
- `--no-debug`: 禁用调试模式
- `--no-wait`: 不等待可视化程序
- `--wait-time [秒数]`: 指定等待可视化程序的时间 (默认: 2.5)
- `--tick-delay [秒数]`: 指定每个tick之间的延迟时间 (默认: 0.3)
- `--help`: 显示帮助信息

**启动顺序**:
1. Elevator Saga 模拟器 (端口 8000)
2. Bus调度算法 (控制电梯运行)
3. 可视化程序 (显示电梯状态)

### stop.bat - 停止脚本

**功能**: 一键关闭所有相关程序

**使用方法**:
```bash
stop.bat
```

## 使用流程

### 推荐使用方式

1. **首次使用**: 使用 `start.bat` 默认配置
2. **日常开发**: 使用 `start.bat` 快速启动
3. **高级配置**: 使用 `start.bat` 配合参数
4. **停止程序**: 使用 `stop.bat` 一键关闭

### 手动启动方式

如果脚本无法正常工作，可以手动启动：

```bash
# 终端1: 启动模拟器
python -m elevator_saga.server.simulator

# 终端2: 启动调度算法
python main.py --controller bus --debug --wait-visualization --tick-delay 0.3

# 终端3: 启动可视化
python run_visualization.py
```

## 注意事项

### 启动顺序
1. **模拟器必须最先启动** - 调度算法和可视化程序依赖模拟器
2. **等待时间** - 脚本会自动等待模拟器启动完成
3. **可视化等待** - 调度算法会等待可视化程序启动（默认2.5秒）
4. **延迟设置** - 默认每个tick延迟0.3秒，便于可视化演示
5. **端口占用** - 确保8000端口未被占用

### 依赖要求
- **Python 3.11+**: 必须安装Python
- **elevator_saga**: 必须安装电梯模拟器模块
- **PyQt6**: 可视化程序需要PyQt6支持
- **requests**: HTTP通信需要requests库

### 故障排除

#### 常见问题
1. **Python未找到**: 确保Python已安装并添加到PATH
2. **模块未找到**: 运行 `pip install -r requirements.txt`
3. **端口被占用**: 关闭占用8000端口的程序
4. **PyQt6错误**: 运行 `pip install PyQt6`

#### 检查步骤
1. 检查Python版本: `python --version`
2. 检查模块安装: `python -c "import elevator_saga"`
3. 检查端口状态: `netstat -an | findstr 8000`
4. 检查PyQt6: `python -c "import PyQt6"`

## 扩展使用

### 添加新的调度算法
1. 在 `controllers/` 目录下创建新的控制器
2. 在 `start.bat` 中添加新的算法选项
3. 在 `main.py` 中添加算法选择逻辑

### 自定义启动参数
修改 `start.bat` 中的默认参数：
```batch
set CONTROLLER=your_algorithm
set MAX_TICKS=5000
set DEBUG_MODE=--debug
```

### 集成到IDE
可以将启动脚本集成到IDE的运行配置中：
- **VS Code**: 在 `.vscode/tasks.json` 中配置
- **PyCharm**: 在运行配置中添加外部工具
- **其他IDE**: 参考相应IDE的外部工具配置

## 性能优化

### 调试模式
- **开启调试**: 显示详细的运行信息，便于调试
- **关闭调试**: 提高运行性能，减少输出

### 延迟设置
- **默认延迟**: 0.3秒，适合可视化演示
- **无延迟**: 设置为0.0，适合性能测试
- **自定义延迟**: 根据需要调整，建议0.1-2.0秒

### 内存管理
- 长时间运行时注意内存使用
- 定期重启程序释放内存
- 监控系统资源使用情况

### 网络优化
- 确保网络连接稳定
- 避免防火墙阻止本地连接
- 检查代理设置
