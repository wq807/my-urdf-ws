from moveit_configs_utils import MoveItConfigsBuilder
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from moveit_configs_utils.launch_utils import (
    add_debuggable_node,
    DeclareBooleanLaunchArg,
)

def generate_launch_description():
    # 适配你的机器人名称和包名
    moveit_config = MoveItConfigsBuilder(
        "six_axis_arm",                     # 必须与 URDF 中 robot name 一致
        package_name="my_robot_moveit_config"
    ).to_moveit_configs()

    ld = LaunchDescription()

    # 声明参数
    ld.add_action(DeclareBooleanLaunchArg("debug", default_value=False))
    ld.add_action(DeclareBooleanLaunchArg("allow_trajectory_execution", default_value=True))
    ld.add_action(DeclareBooleanLaunchArg("publish_monitored_planning_scene", default_value=True))
    ld.add_action(DeclareLaunchArgument("capabilities", default_value=""))
    ld.add_action(DeclareLaunchArgument("disable_capabilities", default_value=""))

    # 构建 move_group 参数
    move_group_params = [
        moveit_config.to_dict(),
        {
            "publish_robot_description_semantic": True,
            "allow_trajectory_execution": LaunchConfiguration("allow_trajectory_execution"),
            "capabilities": LaunchConfiguration("capabilities"),
            "disable_capabilities": LaunchConfiguration("disable_capabilities"),
            "publish_planning_scene": LaunchConfiguration("publish_monitored_planning_scene"),
            "publish_geometry_updates": LaunchConfiguration("publish_monitored_planning_scene"),
            "publish_state_updates": LaunchConfiguration("publish_monitored_planning_scene"),
            "publish_transforms_updates": LaunchConfiguration("publish_monitored_planning_scene"),
            "use_sim_time": True,
        }
    ]

    add_debuggable_node(
        ld,
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=move_group_params,
    )

    # RViz 配置
    ld.add_action(DeclareLaunchArgument(
        "rviz_config",
        default_value=str(moveit_config.package_path / "config" / "moveit.rviz")
    ))

    rviz_params = [
        moveit_config.planning_pipelines,
        moveit_config.robot_description_kinematics,
        {"use_sim_time": True}
    ]

    add_debuggable_node(
        ld,
        package="rviz2",
        executable="rviz2",
        output="log",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        parameters=rviz_params,
    )

    return ld
