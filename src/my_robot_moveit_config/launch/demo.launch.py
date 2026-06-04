import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    # ---------------------- 基础配置（已替换为你实际的文件名） ----------------------
    moveit_config = (
        MoveItConfigsBuilder("my_robot_moveit_config", package_name="my_robot_moveit_config")
        .robot_description(
            file_path="config/episode_urdf_0523.urdf.xacro",
            mappings={"sim_backend": "mock"}
        )
        .robot_description_semantic(file_path="config/episode_urdf_0523.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"], default_planning_pipeline="ompl")
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    # RViz配置文件路径（你的文件里是moveit.rviz，保持不变）
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("my_robot_moveit_config"), "config", "moveit.rviz"]
    )

    # ---------------------- 核心节点启动 ----------------------
    # 1. 启动机械臂状态发布节点
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    # 2. 启动RViz2
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    # 3. 启动控制器管理器（使用你实际的ros2_controllers.yaml）
    controller_manager_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[moveit_config.robot_description, PathJoinSubstitution(
            [FindPackageShare("my_robot_moveit_config"), "config", "ros2_controllers.yaml"]
        )],
        output="both",
    )

    # 4. 加载关节状态广播器
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="both",
    )

    # 5. 加载统一机器人控制器（robot_controller, 8关节）
    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["robot_controller", "--controller-manager", "/controller_manager"],
        output="both",
    )

    # 6. 启动MoveIt2 MoveGroup节点（强制 OMPL，禁用 CHOMP）
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict(),
                    {"planning_plugin": "ompl_interface/OMPLPlanner"},
                    {"default_planning_pipeline": "ompl"}],
    )

    # ---------------------- 启动列表 ----------------------
    return LaunchDescription([
        robot_state_publisher_node,
        controller_manager_node,
        joint_state_broadcaster_spawner,
        robot_controller_spawner,
        move_group_node,
        rviz_node,
    ])
