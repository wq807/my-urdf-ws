#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 包路径配置
    my_robot_moveit_config_pkg = FindPackageShare(package="my_robot_moveit_config").find("my_robot_moveit_config")
    arm_urdf_pkg = get_package_share_directory("arm_urdf")
    gazebo_ros_pkg = get_package_share_directory("gazebo_ros")

    # 启动参数配置
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    world_file = LaunchConfiguration("world_file", default=os.path.join(gazebo_ros_pkg, "worlds", "empty.world"))
    urdf_file_path = os.path.join(arm_urdf_pkg, "urdf", "arm.urdf")

    # 读取URDF文件
    with open(urdf_file_path, "r") as f:
        robot_description_content = f.read()

    # 机器人描述参数
    robot_description = {"robot_description": robot_description_content}

    # 控制器配置文件路径
    ros2_controllers_file = os.path.join(my_robot_moveit_config_pkg, "config", "ros2_controllers.yaml")

    # ---------------------- 1. 启动Gazebo ----------------------
    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, "launch", "gzserver.launch.py")
        ),
        launch_arguments={"world": world_file, "verbose": "true"}.items(),
    )

    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, "launch", "gzclient.launch.py")
        )
    )

    # ---------------------- 2. 机器人状态发布器 ----------------------
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}, robot_description],
    )

    # ---------------------- 3. 在Gazebo中生成机械臂模型 ----------------------
    spawn_robot_node = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_urdf",
        output="screen",
        arguments=["-topic", "robot_description", "-entity", "my_arm", "-x", "0", "-y", "0", "-z", "0"],
    )

    # ---------------------- 4. 控制器管理器与控制器启动 ----------------------
    controller_manager_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, ros2_controllers_file],
        output="screen",
    )

    # 加载关节状态广播器
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"],
        output="screen",
    )

    # 加载关节轨迹控制器
    load_joint_trajectory_controller = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_trajectory_controller"],
        output="screen",
    )

    # ---------------------- 5. 启动MoveIt2 ----------------------
    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(my_robot_moveit_config_pkg, "launch", "moveit_rviz.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    # 事件处理：机械臂生成后再加载控制器
    event_load_controllers = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot_node,
            on_exit=[load_joint_state_broadcaster, load_joint_trajectory_controller],
        )
    )

    # 组装Launch描述
    ld = LaunchDescription()
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(spawn_robot_node)
    ld.add_action(controller_manager_node)
    ld.add_action(event_load_controllers)
    ld.add_action(moveit_launch)

    return ld
