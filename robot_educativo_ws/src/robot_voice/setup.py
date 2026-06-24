from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_voice'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        #  ESTA LÍNEA ES CLAVE: incluir archivos launch
        (os.path.join('share', package_name, 'launch'), 
         glob('launch/*.py')),
        #  También incluir config si tienes
        (os.path.join('share', package_name, 'config'), 
         glob('config/*.yaml')),
        (os.path.join('share', package_name, 'data'), 
         glob('data/**/*', recursive=True)),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Sebastián',
    maintainer_email='sebaaucaaa@gmail.com',
    description='Package para voz del robot educativo',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'voice_node = robot_voice.voice_node:main',
        ],
    },
)
