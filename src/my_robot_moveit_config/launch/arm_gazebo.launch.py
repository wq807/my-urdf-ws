#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess, 
    IncludeLaunchDescription, 
    RegisterEventHandler,
    SetEnvironmentVariable
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # 1. 完全匹配你的包结构和文件路径
    package_name = "my_robot_moveit_config"
    pkg_share = get_package_share_directory(package_name)
    gazebo_ros_share = get_package_share_directory("gazebo_ros")
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    # 匹配你的URDF文件路径和名称
    urdf_path = os.path.join(pkg_share, "config", "episode_urdf_0523.urdf")
    with open(urdf_path, 'r', encoding='utf-8') as infp:
        robot_desc = infp.read()

    # 2. 修复Gazebo模型路径，确保STL网格文件能正常显示
    gazebo_env_resource = SetEnvironmentVariable(
        "GAZEBO_RESOURCE_PATH", 
        f"{pkg_share}:{os.path.join(pkg_share, 'meshes')}:{os.environ.get('GAZEBO_RESOURCE_PATH', '')}"
    )
    gazebo_env_model = SetEnvironmentVariable(
        "GAZEBO_MODEL_PATH", 
        f"{pkg_share}:{os.path.join(pkg_share, 'meshes')}:{os.environ.get('GAZEBO_MODEL_PATH', '')}"
    )

    # 3. 启动Gazebo服务端（物理引擎核心，后台运行）
    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_share, "launch", "gzserver.launch.py")
        ),
        launch_arguments={"world": os.path.join(gazebo_ros_share, "worlds", "empty.world")}.items()
    )

    # 【核心新增】启动Gazebo客户端（图形显示窗口，仅用来显示机械臂，无控制功能）
    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_share, "launch", "gzclient.launch.py")
        )
    )

    # 4. 发布机器人URDF状态，确保模型能被识别
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {"robot_description": robot_desc},
            {"use_sim_time": use_sim_time}
        ],
        output="screen"
    )

    # 5. 将机械臂模型加载到Gazebo场景中
    spawn_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-topic", "robot_description", "-entity", "six_axis_arm"],
        output="screen"
    )

    # 6. 加载控制器（后台运行，无图形界面）
    # 关节状态广播器（必选，控制器核心）
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"],
        output="screen"
    )
    # 关节轨迹控制器（和你的yaml配置完全匹配）
    load_joint_trajectory_controller = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_trajectory_controller"],
        output="screen"
    )

    # 7. 严格控制启动顺序，避免加载失败
    event_after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn_entity, on_exit=[load_joint_state_broadcaster])
    )
    event_after_joint_state = RegisterEventHandler(
        OnProcessExit(target_action=load_joint_state_broadcaster, on_exit=[load_joint_trajectory_controller])
    )

    # 8. 整合所有启动项，顺序不能乱
    return LaunchDescription([
        gazebo_env_resource,
        gazebo_env_model,
        gazebo_server,
        gazebo_client,  # 新增的图形显示窗口，仅此一处改动，其他逻辑完全不变
        robot_state_publisher,
        spawn_entity,
        event_after_spawn,
        event_after_joint_state,
    ])
