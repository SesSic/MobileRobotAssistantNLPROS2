from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_vision'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Incluir archivos launch
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # Incluir archivos de configuración
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Sebastián',
    maintainer_email='sebastian@example.com',
    description='Package para visión del robot educativo',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'usb_camera_node = robot_vision.usb_camera_node:main',
            'calibration_tester = robot_vision.calibration_tester:main',
	    'object_detector_node = robot_vision.object_detector_node:main',
	    'object_follower_node = robot_vision.object_follower_node:main',  # NUEVO
        ],
    },
)
