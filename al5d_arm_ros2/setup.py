from setuptools import setup
import os
from glob import glob

package_name = 'al5d_arm_ros2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            [os.path.join('resource', package_name)]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*launch.[pxy][yma]*')),
        (os.path.join('share', package_name, 'config'), glob('config/*.*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.*')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.*')),
        # if you have meshes, adjust path accordingly or remove if not needed in simulation
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*.*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kimbring2',
    maintainer_email='kimbring2@gmail.com',
    description='Simulation and gesture-driven control for the AL5D robotic arm using ROS2 Humble, Gazebo, and ros2_control.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'controller = al5d_arm_ros2.al5d_arm_controller:main',
            'gesture_to_arm = al5d_arm_ros2.gesture_to_arm:main',
            'test = al5d_arm_ros2.test:main',
        ],
    },
)

