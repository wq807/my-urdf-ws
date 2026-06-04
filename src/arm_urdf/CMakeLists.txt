cmake_minimum_required(VERSION 3.8)
project(arm_urdf)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 仅保留真正需要的编译依赖（删除错误的launch_ros）
find_package(ament_cmake REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(gazebo_ros2_control REQUIRED)
find_package(ros2_control REQUIRED)
find_package(ros2_controllers REQUIRED)

# 安装资源文件，确保urdf/meshes/launch/config被ROS正确识别
install(
  DIRECTORY urdf meshes launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
