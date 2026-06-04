import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    # 1. 获取功能包路径
    pkg_name = 'arm_urdf'
    pkg_share_dir = get_package_share_directory(pkg_name)

    # 2. 加载你的URDF模型（和Gazebo用同一个文件，完全通用）
    urdf_file_path = os.path.join(pkg_share_dir, 'urdf', 'arm.urdf')
    robot_description_config = xacro.process_file(urdf_file_path)
    robot_description = {'robot_description': robot_description_config.toxml()}

    # 3. 机器人状态发布器（必须有，负责发布模型坐标）
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    # 4. 关节控制GUI（拖动滑块控制机械臂）
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen'
    )

    # 5. 启动RViz2（自动加载基础配置）
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_share_dir, 'rviz', 'arm_config.rviz')]
    )

    return LaunchDescription([
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
