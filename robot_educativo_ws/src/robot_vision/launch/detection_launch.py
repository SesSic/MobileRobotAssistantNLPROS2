#!/usr/bin/env python3
"""
Launch file para sistema de detección de objetos
Lanza cámara USB + detector de objetos
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    # Argumentos de lanzamiento
    camera_id_arg = DeclareLaunchArgument(
        'camera_id',
        default_value='0',
        description='ID de la cámara USB (0 para integrada, 1 para USB)'
    )
    
    model_path_arg = DeclareLaunchArgument(
        'models_path',
        default_value=PathJoinSubstitution([
            FindPackageShare('robot_vision'),
            'models'
        ]),
        description='Ruta a los modelos YOLO'
    )
    
    confidence_arg = DeclareLaunchArgument(
        'confidence',
        default_value='0.25',
        description='Umbral de confianza para detecciones'
    )
    
    # Nodo de cámara USB
    usb_camera_node = Node(
        package='robot_vision',
        executable='usb_camera_node',
        name='usb_camera_node',
        parameters=[{
            'camera_id': LaunchConfiguration('camera_id'),
            'width': 640,
            'height': 480,
            'fps': 15,  # Reducido para Raspberry Pi
            'frame_id': 'usb_camera_link',
        }],
        output='log',
        remappings=[
            ('image_raw', '/camera/image_raw'),
            ('camera_info', '/camera/camera_info')
        ]
    )
    
    # Nodo de detección de objetos
    detector_node = Node(
        package='robot_vision',
        executable='object_detector_node',
        name='object_detector_node',
        parameters=[{
            'model.yolo': 'yolov8n.pt',
            'model.door': 'door_model/best.pt',  # Ajustar si existe
            'confidence_threshold': LaunchConfiguration('confidence'),
            'publish_rate': 2.0,  # Hz
            'enable_visualization': True,
            'models_path': LaunchConfiguration('models_path'),
        }],
        output='log',
        remappings=[
            ('/image_raw', '/camera/image_raw')
        ]
    )
    
    # Mensaje informativo
    info_msg = LogInfo(
        msg=f"Sistema de detección iniciado. "
            f"Cámara ID: {LaunchConfiguration('camera_id')}, "
            f"Confianza: {LaunchConfiguration('confidence')}"
    )
    
    return LaunchDescription([
        camera_id_arg,
        model_path_arg,
        confidence_arg,
        usb_camera_node,
        detector_node,
        info_msg
    ])