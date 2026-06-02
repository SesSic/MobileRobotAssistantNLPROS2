#!/bin/bash
# start_robot.sh - Inicia todos los nodos del robot

# ============ CONFIGURACIÓN DE ENTORNO COMPLETA ============

# 1. PATH general (incluye ~/.local/bin para edge-tts)
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/home/sessic/.local/bin:$PATH"

# 2. Directorio personal (para rutas relativas)
export HOME="/home/sessic"

# 3. Python path (para librerías instaladas con pip)
export PYTHONPATH="/home/sessic/.local/lib/python3.10/site-packages:$PYTHONPATH"

# 4. Directorio de modelos VOSK (¡IMPORTANTE!)
export VOSK_MODEL_PATH="/home/sessic/model-vosk-es-small"

# 5. Directorio de Piper
export PIPER_PATH="/home/sessic/piper"

# 6. Variables de ROS
export ROS_DOMAIN_ID=0
source /opt/ros/humble/setup.bash
source /home/sessic/robot_educativo_ws/install/setup.bash

# ============ IR A DIRECTORIOS NECESARIOS ============
cd /home/sessic/piper  # Para que Piper encuentre sus modelos

# ============ LANZAR EL ROBOT ============
ros2 launch robot_voice voice_launch.py

sleep 5

wait