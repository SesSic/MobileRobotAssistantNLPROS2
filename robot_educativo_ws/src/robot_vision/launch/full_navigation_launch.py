#!/usr/bin/env python3
"""
Launch file para sistema completo: Visión + Seguimiento + Navegación
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    # Argumentos
    camera_id_arg = DeclareLaunchArgument(
        'camera_id',
        default_value='0',
        description='ID de la cámara USB'
    )
    
    # 1. SISTEMA DE VISIÓN
    detection_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_vision'),
                'launch',
                'detection_launch.py'
            ])
        ]),
        launch_arguments={
            'camera_id': LaunchConfiguration('camera_id'),
            'confidence': '0.3'
        }.items()
    )
    
    # 2. NODO DE SEGUIMIENTO
    follower_node = Node(
        package='robot_vision',
        executable='object_follower_node',
        name='object_follower_node',
        parameters=[{
            'linear_speed': 0.12,
            'angular_speed': 0.35,
            'target_distance': 0.8,
            'stop_distance': 0.4,
            'follow_timeout': 2.5
        }],
        output='screen'
    )
    
    # 3. NAVEGACIÓN (si quieres evitar obstáculos automáticamente)
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_navigation'),
                'launch',
                'nav_bringup.launch.py'
            ])
        ])
    )
    
    return LaunchDescription([
        camera_id_arg,
        detection_launch,
        follower_node,
        nav_launch,
        LogInfo(msg="=== SISTEMA COMPLETO INICIADO ===")
    ])