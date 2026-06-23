from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Obtener ruta del paquete
    pkg_dir = get_package_share_directory('robot_vision')
    
    # Ruta al archivo de calibración
    calib_file = os.path.join(pkg_dir, 'config', 'usb_camera_calibration.yaml')
    
    # Nodo de cámara USB con parámetros
    usb_camera_node = Node(
        package='robot_vision',
        executable='usb_camera_node',
        name='usb_camera_node',
        parameters=[
            {'camera_id': 0},
            {'width': 640},
            {'height': 480},
            {'fps': 30},
            {'frame_id': 'usb_camera_link'},
            {'camera_info_url': f'file://{calib_file}'}
        ],
        output='screen'
    )
    
    return LaunchDescription([
        usb_camera_node
    ])