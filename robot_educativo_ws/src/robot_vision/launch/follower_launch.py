#!/usr/bin/env python3
"""
Launch file para sistema de seguimiento de objetos
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Argumentos
    linear_speed_arg = DeclareLaunchArgument(
        'linear_speed',
        default_value='0.15',
        description='Velocidad lineal máxima (m/s)'
    )
    
    target_distance_arg = DeclareLaunchArgument(
        'target_distance',
        default_value='0.8',
        description='Distancia deseada al objeto (m)'
    )
    
    # Nodo seguidor
    follower_node = Node(
        package='robot_vision',
        executable='object_follower_node',
        name='object_follower_node',
        parameters=[{
            'linear_speed': LaunchConfiguration('linear_speed'),
            'angular_speed': 0.4,
            'target_distance': LaunchConfiguration('target_distance'),
            'stop_distance': 0.4,
            'follow_timeout': 3.0,
        }],
        output='screen'
    )
    
    return LaunchDescription([
        linear_speed_arg,
        target_distance_arg,
        follower_node,
        LogInfo(msg="Sistema de seguimiento de objetos iniciado")
    ])
