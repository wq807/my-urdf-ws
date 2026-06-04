from setuptools import setup

package_name = 'my_moveit_demo'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wq',
    maintainer_email='wq@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    # 核心：在这里注册你的Python节点
    entry_points={
        'console_scripts': [
            # 格式：节点名 = 包名.脚本名:main函数
            'motion_plan = my_moveit_demo.motion_plan:main',
        ],
    },
)
