#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Nodo de cámara (que ya tienes)
        Node(
            package='robot_vision',
            executable='usb_camera_node',
            name='usb_camera_node',
            parameters=[{'camera_id': 2}],
            output='log'
        ),
        
        # 2. Nodo ultrasónico
        Node(
            package='robot_navigation',
            executable='ultrasonic_node',
            name='ultrasonic_node',
            output='log'
        ),
        
        # 3. Nodo de navegación
        Node(
            package='robot_navigation',
            executable='navigation_node',
            name='navigation_node',
            parameters=[{'debug': False}],
            output='log'
        ),
        
        # 4. Controlador de motores
        Node(
            package='robot_navigation',
            executable='motor_controller_node',
            name='motor_controller_node',
            output='log'
        ),
        
        # 5. Visualización (opcional)
        Node(
            package='rqt_image_view',
            executable='rqt_image_view',
            name='image_view',
            arguments=['/image_raw']
        ),
    ])