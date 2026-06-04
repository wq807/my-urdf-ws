# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 环境

- **ROS2 distro**: Humble (Ubuntu 22.04 WSL2)
- **构建系统**: colcon
- **Python**: 3.10
- **几乎所有命令前都需要**: `. install/setup.bash`

## 构建与测试命令

```bash
# 构建所有包
colcon build

# 只构建单个包（迭代开发更快）
colcon build --packages-select arm_urdf
colcon build --packages-select my_robot_moveit_config
colcon build --packages-select my_moveit_demo

# symlink 安装（Python 包修改代码后无需重新构建）
colcon build --symlink-install

# 运行测试（仅 my_moveit_demo 有测试，arm_urdf 和 my_robot_moveit_config 无测试）
colcon test --packages-select my_moveit_demo

# 运行单个测试
colcon test --packages-select my_moveit_demo --pytest-args -k test_flake8

# 直接在控制台显示测试输出
colcon test --packages-select my_moveit_demo --event-handlers console_direct+
```

## 包结构与架构

工作空间包含三个 ROS2 包：

### `arm_urdf` — 机械臂 URDF 模型 + 基础 Gazebo 仿真

C++/CMake 包（ament_cmake）。提供从 SolidWorks 导出的原始机器人模型。

- **`urdf/arm.urdf`** — 完整机器人模型：6个旋转关节(J1–J6)，6个连杆(L1–L6) + base_link + world link，含惯性/碰撞/可视化属性、transmission模块、gazebo_ros2_control 插件。由 sw_urdf_exporter 插件从 SolidWorks 生成。
- **`meshes/*.STL`** — 每个连杆的碰撞和可视化网格文件。
- **`launch/arm_gazebo.launch.py`** — 主要 launch 文件。启动 Gazebo + robot_state_publisher + spawn_entity，然后通过事件处理器链式加载 `joint_state_broadcaster` 和 `arm_trajectory_controller`。
- **`launch/gazebo_launch.py`** — 备选 Gazebo launch（使用 xacro，不含控制器加载，含 joint_state_publisher_gui）。
- **`launch/rviz_launch.py`** — 纯 RViz launch（无 Gazebo），使用 joint_state_publisher_gui 手动测试关节。依赖 `rviz/arm_config.rviz` 文件。
- **`config/arm_controllers.yaml`** — 控制器管理器配置：定义 `joint_state_broadcaster` 和 `joint_trajectory_controller`（J1–J6，位置接口）。
- **`config/joint_names_*.yaml`** — 控制器关节名称映射。

### `my_robot_moveit_config` — MoveIt2 配置包（Setup Assistant 生成）

C++/CMake 包（ament_cmake）。由 MoveIt Setup Assistant 自动生成，是机械臂运动规划的核心配置包。**被 `arm_urdf` 的 URDF 中 ros2_control 插件所引用。**

- **`config/episode_urdf_0523.urdf.xacro`** — 机械臂 xacro 宏定义。
- **`config/episode_urdf_0523.srdf`** — 语义机器人描述：定义了规划组 `arm`（base_link → L6 运动链）、`home` 姿态、相邻/不相邻连杆的碰撞禁用对、虚拟关节（world → base_link）、末端执行器(L6)。
- **`config/ros2_controllers.yaml`** — 控制器配置（`joint_state_broadcaster` + `joint_trajectory_controller`），各关节含独立轨迹约束(trajectory: 0.5, goal: 0.05)。
- **`config/kinematics.yaml`** — 运动学求解器配置。
- **`config/joint_limits.yaml`** — 关节位置/速度/加速度限制。
- **`config/ompl_planning.yaml`** — OMPL 规划器配置。
- **`config/moveit_controllers.yaml`** — MoveIt 端控制器映射（`FollowJointTrajectory` action 接口）。
- **`config/moveit.rviz`** — RViz 预设布局。
- **`launch/gazebo_moveit_full.launch.py`** — **最完整的 launch 文件**：同时启动 Gazebo 仿真 + 控制器加载 + MoveGroup + RViz。含 `GAZEBO_MODEL_PATH` 硬编码修复（指向 install 目录下的 STL 文件路径）。
- **`launch/demo.launch.py`** — 纯 RViz + MoveGroup（无 Gazebo），使用 `MoveItConfigsBuilder` API 加载配置。
- **`launch/move_group.launch.py`** — 单独启动 MoveGroup。
- **`launch/rsp.launch.py`** — 单独的 robot_state_publisher。
- **`launch/spawn_controllers.launch.py`** — 单独的控制器 spawner。
- **`launch/setup_assistant.launch.py`** — 启动 MoveIt Setup Assistant 进行配置调整。

### `my_moveit_demo` — MoveIt2 Python 运动规划演示

Python 包（ament_python）。轻量级运动规划演示，使用 `pymoveit2`。

- **`my_moveit_demo/motion_plan.py`** — 单节点：创建 MoveIt2 实例（planning group=`"arm"`, base frame=`"base_link"`, end effector=`"L6"`, 关节 J1–J6），通过 `move_to_configuration()` 移动到安全中间姿态 `[0.0, -0.3, 0.3, 0.0, 0.3, 0.0]`。
- **`setup.py`** — 注册入口点 `motion_plan = my_moveit_demo.motion_plan:main`，可直接运行 `ros2 run my_moveit_demo motion_plan`。
- **测试** (`test/`) — 标准 ROS2 模板测试（copyright, flake8, pep257），目前因源代码无版权头、代码风格问题而被跳过。

## 启动仿真

```bash
# 完整 Gazebo 仿真 + 控制器（arm_urdf 自己的 launch）
ros2 launch arm_urdf arm_gazebo.launch.py

# Gazebo + MoveGroup + RViz（最完整，推荐用于 MoveIt 开发）
ros2 launch my_robot_moveit_config gazebo_moveit_full.launch.py

# 仅 RViz + MoveGroup（无物理仿真，快速测试运动规划）
ros2 launch my_robot_moveit_config demo.launch.py

# 仅 RViz（无 Gazebo，手动滑块控制关节）
ros2 launch arm_urdf rviz_launch.py

# 运行 MoveIt2 运动规划演示（Gazebo 已启动且控制器已加载后）
ros2 run my_moveit_demo motion_plan
```

## 关键依赖关系

- **`arm_urdf` ↔ `my_robot_moveit_config`**: `arm.urdf` 中的 ros2_control 插件通过 `$(find my_robot_moveit_config)` 引用后者的 `ros2_controllers.yaml`。两者必须同时构建安装。
- **`ros2_control` + `gazebo_ros2_control`**: 桥接 ROS2 控制器与 Gazebo 物理引擎。
- **`joint_state_broadcaster`**: 发布 `/joint_states` 话题。
- **`joint_trajectory_controller`**: 接收 `FollowJointTrajectory` action 目标。
- **`pymoveit2`**: MoveIt2 Python 绑定（`my_moveit_demo` 使用）。
- **`robot_state_publisher`**: 从 URDF 发布 TF 坐标变换。

## 注意事项

- WSL2 环境下，WSL 内部路径为 `/home/wq77/...`，Windows 侧对应 `\\wsl.localhost\Ubuntu-22.04\home\wq77\...`。文件含大量 `:Zone.Identifier` 附属文件（Windows 标记文件），git 已忽略。
- `gazebo_moveit_full.launch.py` 中 `GAZEBO_MODEL_PATH` 硬编码了 `/home/wq77/urdf_ws/install/...` 路径，若移动工作空间需相应修改。
- `arm_urdf` 和 `my_robot_moveit_config` 都有各自的 `arm.urdf` 和 STL 网格副本，修改模型时需要两边同步。
