from setuptools import find_packages, setup

package_name = 'fingers'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='heni',
    maintainer_email='heni@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'auto_recorder_node = fingers.auto_recorder_node:main',
            'train_mlp = fingers.train_mlp:main',
            
        ],
    },
)
