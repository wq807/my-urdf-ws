from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("episode_urdf_0523", package_name="my_robot_moveit_config")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .planning_pipelines(pipelines=["ompl"], default_planning_pipeline="ompl")
        .to_moveit_configs()
    )
    moveit_config.update({
        "planning_plugin": "ompl_interface/OMPLPlanner",
        "default_planning_pipeline": "ompl",
    })
    return generate_move_group_launch(moveit_config)
