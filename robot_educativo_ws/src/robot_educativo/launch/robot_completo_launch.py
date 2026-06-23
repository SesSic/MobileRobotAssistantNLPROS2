#!/usr/bin/env python3
"""
LAUNCH COMPLETO DEL ROBOT EDUCATIVO
Con todos los nodos:
- Visión (cámara + detección)
- Voz (VOSK + procesador)
- Navegación (motores + ultrasonido + IMU)
- Seguimiento de objetos
- Anuncio de inicio (después de 10 segundos)
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. MOTORES (siempre activos)
        Node(
            package='robot_navigation',
            executable='motor_controller_node',
            name='motor_controller_node',
            output='log',
        ),
        
        # 2. ULTRASONIDO
        Node(
            package='robot_navigation',
            executable='ultrasonic_node',
            name='ultrasonic_node',
            output='log',
        ),
        
        # 3. IMU
        Node(
            package='robot_navigation',
            executable='imu_odometry_node',
            name='imu_odometry_node',
            output='log',
        ),
        
        # 4. VISIÓN (cámara + detector)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('robot_vision'),
                    'launch',
                    'detection_launch.py'
                ])
            ]),
            launch_arguments={
                'camera_id': '0',
                'confidence': '0.25'
            }.items()
        ),
        
        # 5. SEGUIDOR DE OBJETOS (inicia inactivo)
        Node(
            package='robot_vision',
            executable='object_follower_node',
            name='object_follower_node',
            output='log',
        ),
        
        # 6. VOZ
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('robot_voice'),
                    'launch',
                    'voice_launch.py'
                ])
            ]),
            launch_arguments={
                'mic_device': 'hw:1,0',
                'speaker_device': 'plughw:2,0'
            }.items()
        ),
        
        # 7. ANUNCIO DE INICIO (después de 10 segundos)
        TimerAction(
            period=10.0,
            actions=[
                Node(
                    package='robot_voice',
                    executable='voice_node',
                    name='startup_announcer',
                    arguments=['--ros-args', '-p', f'startup_message:=Sistema cargado completamente. ¿En qué puedo ayudarte el día de hoy?'],
                    output='log',
                )
            ]
        ),
        
        LogInfo(msg="""
╔══════════════════════════════════════════════════════════╗
║   ROBOT EDUCATIVO - SISTEMA COMPLETO                     ║
╠══════════════════════════════════════════════════════════╣
║   Motores listos                                         ║
║   Ultrasonido activo                                     ║
║   IMU calibrada                                          ║
║   Cámara funcionando                                     ║
║   Detector YOLO listo                                    ║
║   Voz activa                                             ║
║   Seguidor de objetos esperando                          ║
║   Anuncio de inicio en 10 segundos...                    ║
╚══════════════════════════════════════════════════════════╝
        """),
    ])