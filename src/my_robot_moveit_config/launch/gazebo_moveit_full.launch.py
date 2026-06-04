import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # ================== 1. 路径与环境变量硬核锁死 ==================
    pkg_my_robot_moveit_config = get_package_share_directory("my_robot_moveit_config")

    # 【核心修复】直接在 Python 内部强行拼接并覆盖这两个包的绝对 share 路径
    # 这样 Gazebo 图形界面启动时，绝对能顺着路径摸到你的机械臂 STL 模型文件
    os.environ["GAZEBO_MODEL_PATH"] = (
            os.environ.get("GAZEBO_MODEL_PATH", "") +
            ":" + "/home/wq77/urdf_ws/install/my_robot_moveit_config/share/" +
            ":" + "/home/wq77/urdf_ws/install/arm_urdf/share/"
    )

    xacro_file = os.path.join(pkg_my_robot_moveit_config, "config", "episode_urdf_0523.urdf.xacro")
    srdf_file = os.path.join(pkg_my_robot_moveit_config, "config", "episode_urdf_0523.srdf")
    kinematics_config = os.path.join(pkg_my_robot_moveit_config, "config", "kinematics.yaml")
    ompl_planning_config = os.path.join(pkg_my_robot_moveit_config, "config", "ompl_planning.yaml")
    joint_limits_config = os.path.join(pkg_my_robot_moveit_config, "config", "joint_limits.yaml")
    moveit_controllers_config = os.path.join(pkg_my_robot_moveit_config, "config", "moveit_controllers.yaml")
    rviz_config_file = os.path.join(pkg_my_robot_moveit_config, "config", "moveit.rviz")

    robot_description_content = Command(['xacro ', xacro_file])

    with open(srdf_file, "r") as infp:
        robot_description_semantic_content = infp.read()

    robot_description = {"robot_description": robot_description_content}
    robot_description_semantic = {"robot_description_semantic": robot_description_semantic_content}
    use_sim_time = {"use_sim_time": True}

    # 同时拉起前端 GUI 和后端物理引擎
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])]
        ),
        launch_arguments={"verbose": "false"}.items(),
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description, use_sim_time],
    )

    spawn_entity_node = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-topic", "robot_description", "-entity", "six_axis_arm"],
        output="screen",
    )

    # ================= 2. 标准事件驱动控制序列 =================
    set_use_sim_time_cmd = ExecuteProcess(
        cmd=["ros2", "param", "set", "/controller_manager", "use_sim_time", "true"],
        output="screen",
    )

    load_joint_state_broadcaster = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"],
        output="screen",
    )

    load_joint_trajectory_controller = ExecuteProcess(
        cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_trajectory_controller"],
        output="screen",
    )

    # 当机械臂成功生成（spawn_entity 结束）后 -> 立刻同步时钟并加载状态广播器
    delay_after_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity_node,
            on_exit=[set_use_sim_time_cmd, load_joint_state_broadcaster],
        )
    )

    # 当状态广播器加载完成后 -> 再去拉起轨迹控制器
    delay_after_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_joint_trajectory_controller],
        )
    )

    ompl_pipeline_config = {
        "ompl": {
            "planning_plugin": "ompl_interface/OMPLPlanner",
            "request_adapters": "default_planner_request_adapters/AddTimeOptimalParameterization default_planner_request_adapters/FixWorkspaceBounds default_planner_request_adapters/FixStartStateBounds default_planner_request_adapters/FixStartStateCollision default_planner_request_adapters/FixStartStatePathConstraints",
            "start_state_max_bounds_error": 0.1,
        }
    }

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_config,
            ompl_planning_config,
            joint_limits_config,
            moveit_controllers_config,
            ompl_pipeline_config,
            use_sim_time,
            {"default_planning_pipeline": "ompl"},
            {"planning_plugin": "ompl_interface/OMPLPlanner"},
            {
                "request_adapters": "default_planner_request_adapters/AddTimeOptimalParameterization default_planner_request_adapters/FixWorkspaceBounds default_planner_request_adapters/FixStartStateBounds default_planner_request_adapters/FixStartStateCollision default_planner_request_adapters/FixStartStatePathConstraints"},
            {"publish_robot_description_semantic": True},
            {"allow_trajectory_execution": True},
            {"max_safe_path_cost": 1.0},
            {"jiggle_fraction": 0.05},
            {"manage_controllers": False},
            # 允许起始点和真实仿真器之间有 0.1 弧度的位置偏差容忍度（解决重力下坠报错）
            {"trajectory_execution.allowed_start_tolerance": 0.1},
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_config,
            joint_limits_config,
            moveit_controllers_config,
            use_sim_time,
        ],
    )

    return LaunchDescription(
        [
            gazebo,
            robot_state_publisher_node,
            spawn_entity_node,
            delay_after_spawn,
            delay_after_broadcaster,
            move_group_node,
            rviz_node,
        ]
    )