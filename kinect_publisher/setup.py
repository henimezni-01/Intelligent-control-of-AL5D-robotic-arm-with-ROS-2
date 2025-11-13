from setuptools import find_packages, setup
import os

package_name = 'kinect_publisher'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Si tu as un dossier resource/kinect_publisher, sinon retire cette ligne
        # ('share/ament_index/resource_index/packages',
        #  ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='heni',
    maintainer_email='heni@todo.todo',
    description='TODO: Package description',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'kinect_node = kinect_publisher.kinect_node:main',
        ],
    },
)

