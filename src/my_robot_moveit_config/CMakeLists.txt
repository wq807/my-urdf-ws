cmake_minimum_required(VERSION 3.22)
project(my_robot_moveit_config)

find_package(ament_cmake REQUIRED)

# 安装 launch 文件夹（自动包含所有 .launch.py 文件，排除无用文件）
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/launch")
  install(
    DIRECTORY launch config meshes urdf
    DESTINATION share/${PROJECT_NAME}
    PATTERN "setup_assistant.launch" EXCLUDE
  )
endif()

# 安装 config 配置文件夹
install(DIRECTORY config DESTINATION share/${PROJECT_NAME})

# 安装配置文件
install(FILES .setup_assistant DESTINATION share/${PROJECT_NAME})

# 【核心修复】ament_package() 必须放在文件最后！
ament_package()
