#!/usr/bin/env python3
"""
Launch file para sistema de voz unificado
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Argumentos
    mic_device_arg = DeclareLaunchArgument(
        'mic_device',
        default_value='hw:1,0',
        description='Dispositivo de micrófono'
    )
    
    speaker_device_arg = DeclareLaunchArgument(
        'speaker_device',
        default_value='plughw:2,0',
        description='Dispositivo de parlante'
    )
    
    vosk_model_arg = DeclareLaunchArgument(
        'vosk_model',
        default_value='/home/sessic/robot_educativo_ws/model-vosk-es-small',
        description='Ruta al modelo VOSK'
    )
    
    # Nodo de voz unificado con mensaje de inicio FIJO
    voice_node = Node(
        package='robot_voice',
        executable='voice_node',
        name='voice_node',
        output='log',
        parameters=[{
            'audio.device.mic': LaunchConfiguration('mic_device'),
            'audio.device.speaker': LaunchConfiguration('speaker_device'),
            'vosk.model_path': LaunchConfiguration('vosk_model'),
            'startup_message': 'Sistema cargado en modo educacion. ¿En qué puedo ayudarte el día de hoy?',  #  MENSAJE FIJO AQUÍ
            'keyword': 'robot',
            'motor.auto_stop_duration': 2.0,
            'motor.speed_linear': 0.18,
            'motor.speed_angular': 2.5,
        }]
    )
    
    info_msg = LogInfo(
        msg="\n SISTEMA DE VOZ UNIFICADO INICIADO\n"
            "   Di: 'Robot adelante' para movimiento\n"
            "   Di: 'Robot ¿qué ves?' para visión\n"
            "   Di: 'Robot ¿cuánto es 2+2?' para preguntas académicas"
    )
    
    return LaunchDescription([
        mic_device_arg,
        speaker_device_arg,
        vosk_model_arg,
        voice_node,
        info_msg
    ])