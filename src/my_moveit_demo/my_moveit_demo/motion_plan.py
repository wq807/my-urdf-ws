#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from pymoveit2 import MoveIt2

def main():
    rclpy.init()

    # 100%匹配你的参数
    PLANNING_GROUP = "arm_with_gripper"
    BASE_FRAME = "base_link"
    END_EFFECTOR_NAME = "L6"
    JOINT_NAMES = ["J1", "J2", "J3", "J4", "J5", "J6", "gripper_left_joint"]

    node = Node("move_to_mid_pose")
    moveit2 = MoveIt2(
        node=node,
        group_name=PLANNING_GROUP,
        joint_names=JOINT_NAMES,
        base_link_name=BASE_FRAME,
        end_effector_name=END_EFFECTOR_NAME,
    )

    import threading
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # 先把机械臂移到一个安全的中间姿态（零位附近，无碰撞）
    safe_mid_joints = [0.0, -0.3, 0.3, 0.0, 0.3, 0.0, 0.0475]
    node.get_logger().info("=== 移动到安全中间姿态 ===")
    moveit2.move_to_configuration(safe_mid_joints)
    node.get_logger().info("✅ 已到达安全中间姿态")

    rclpy.shutdown()
    spin_thread.join()

if __name__ == "__main__":
    main()
