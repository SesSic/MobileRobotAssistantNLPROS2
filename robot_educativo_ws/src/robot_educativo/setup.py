from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_educativo'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Incluir archivos launch
        (os.path.join('share', package_name, 'launch'), 
         glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sessic',
    maintainer_email='sessic@todo.todo',
    description='Paquete principal del robot educativo',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Si tienes nodos en este paquete, agrégalos aquí
        ],
    },
)