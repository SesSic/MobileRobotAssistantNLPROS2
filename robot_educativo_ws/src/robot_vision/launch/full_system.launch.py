#!/usr/bin/env python3
"""
 LAUNCH COMPLETO: Visión + Voz
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Lanzar sistema de visión
    vision_launch = IncludeLaunchDescription(
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
    )
    
    # Lanzar sistema de voz
    voice_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('robot_voice'),
                'launch',
                'voice_launch.py'
            ])
        ]),
        launch_arguments={
            'mic_device': 'hw:2,0',
            'speaker_device': 'plughw:1,0'
        }.items()
    )
    
    info_msg = LogInfo(
        msg=" SISTEMA COMPLETO INICIADO\n"
            "   Visión: Detectando objetos\n"
            "   Voz: Escuchando comandos\n"
            "   Di: '¿qué ves?' para obtener descripción"
    )
    
    return LaunchDescription([
        vision_launch,
        voice_launch,
        info_msg
    ])
