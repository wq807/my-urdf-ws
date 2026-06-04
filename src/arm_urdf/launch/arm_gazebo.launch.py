import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # 1. 配置功能包和URDF路径
    package_name = "arm_urdf"
    urdf_file_name = "arm.urdf"  # 你的URDF文件名，不一致请修改
    urdf_path = os.path.join(
        get_package_share_directory(package_name),
        "urdf",
        urdf_file_name
    )

    # 2. 加载URDF文件
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()

    # 3. 启动Gazebo仿真环境
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("gazebo_ros"),
                "launch",
                "gazebo.launch.py"
            )
        )
    )

    # 4. 发布机器人状态（URDF到ROS2参数服务器）
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_desc, "use_sim_time": True}],
    )

    # 5. 将机械臂模型加载到Gazebo
    spawn_entity_node = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_urdf",
        output="screen",
        arguments=["-topic", "robot_description", "-entity", "six_axis_arm"],
    )

    # 6. 加载关节状态发布器（MoveIt2/控制器必备）
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"],
        output="screen"
    )

    # 7. 加载机械臂轨迹控制器
    load_arm_trajectory_controller = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "arm_trajectory_controller"],
        output="screen"
    )

    # 8. 严格控制启动顺序（Humble完全兼容版）
    # 顺序：Gazebo启动 → 模型加载完成 → 加载关节状态发布器 → 加载轨迹控制器
    event_load_joint_state = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity_node,
            on_exit=[load_joint_state_broadcaster],
        )
    )
    event_load_trajectory = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_arm_trajectory_controller],
        )
    )

    # 9. 整合所有启动节点
    return LaunchDescription([
        gazebo,
        robot_state_publisher_node,
        spawn_entity_node,
        event_load_joint_state,
        event_load_trajectory,
    ])
