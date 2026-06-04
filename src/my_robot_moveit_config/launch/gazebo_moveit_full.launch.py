import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

# ================= 新增：YAML 字典读取函数 =================
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def generate_launch_description():
    # ================== 1. 路径与环境变量硬核锁死 ==================
    pkg_my_robot_moveit_config = get_package_share_directory("my_robot_moveit_config")

    # 直接在 Python 内部强行拼接并覆盖这两个包的绝对 share 路径
    os.environ["GAZEBO_MODEL_PATH"] = (
            os.environ.get("GAZEBO_MODEL_PATH", "") +
            ":" + "/home/wq77/urdf_ws/install/my_robot_moveit_config/share/" +
            ":" + "/home/wq77/urdf_ws/install/arm_urdf/share/"
    )

    xacro_file = os.path.join(pkg_my_robot_moveit_config, "config", "episode_urdf_0523.urdf.xacro")
    srdf_file = os.path.join(pkg_my_robot_moveit_config, "config", "episode_urdf_0523.srdf")
    
    # ================= 核心修复：提前将 yaml 读取为 Python 字典 =================
    kinematics_dict = load_yaml(os.path.join(pkg_my_robot_moveit_config, "config", "kinematics.yaml"))
    ompl_planning_dict = load_yaml(os.path.join(pkg_my_robot_moveit_config, "config", "ompl_planning.yaml"))
    joint_limits_dict = load_yaml(os.path.join(pkg_my_robot_moveit_config, "config", "joint_limits.yaml"))
    moveit_controllers_dict = load_yaml(os.path.join(pkg_my_robot_moveit_config, "config", "moveit_controllers.yaml"))

    rviz_config_file = os.path.join(pkg_my_robot_moveit_config, "config", "moveit.rviz")

    robot_description_content = Command(['xacro ', xacro_file, ' sim_backend:=gazebo'])

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

    # ================= 2. 控制器加载（使用 spawner，内置重试机制） =================
    # spawner 会等待 controller_manager 的 service 可用后自动重试，
    # 不会像 ros2 control load_controller 那样静默失败

    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager", "--activate"],
        output="screen",
    )

    load_robot_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["robot_controller", "-c", "/controller_manager", "--activate"],
        output="screen",
    )

    # 事件链：spawn_entity → joint_state_broadcaster → robot_controller
    delay_after_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity_node,
            on_exit=[load_joint_state_broadcaster],
        )
    )

    delay_after_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_robot_controller],
        )
    )

    # ================= 核心修复：完美注册 OMPL 管道和时间戳生成器 =================
    ompl_pipeline_config = {
        "planning_pipelines": ["ompl"],  # 显式注册 ompl，防止退回 CHOMP
        "default_planning_pipeline": "ompl",
        "ompl": {
            "planning_plugin": "ompl_interface/OMPLPlanner",
            # 下面这行就是解决 "Time is 0.0000" 报错的救命稻草：自动为轨迹添加时间戳和速度、加速度限制
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
            kinematics_dict,
            ompl_planning_dict,
            joint_limits_dict,
            moveit_controllers_dict,
            ompl_pipeline_config, # 将上方配置完美注入
            use_sim_time,
            {"publish_robot_description_semantic": True},
            {"allow_trajectory_execution": True},
            {"manage_controllers": False},
            {"trajectory_execution.allowed_start_tolerance": 0.1},  # 允许 Gazebo 初始抖动带来的误差
            {"trajectory_execution.allowed_goal_tolerance": 0.1},
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
            kinematics_dict,          # 已修复：传入字典
            joint_limits_dict,        # 已修复：传入字典
            moveit_controllers_dict,  # 已修复：传入字典
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