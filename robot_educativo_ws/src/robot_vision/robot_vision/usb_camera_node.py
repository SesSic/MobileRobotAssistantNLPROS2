#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import cv2
import yaml
import os
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from camera_info_manager import CameraInfoManager
from rclpy.parameter import Parameter

class USBCameraNode(Node):
    def __init__(self):
        super().__init__('usb_camera_node')
        
        # Parámetros configurables
        self.declare_parameter('camera_id', 0)
        self.declare_parameter('frame_id', 'usb_camera_link')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('camera_info_url', '')
        
        # Obtener parámetros
        camera_id = self.get_parameter('camera_id').value
        self.frame_id = self.get_parameter('frame_id').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        fps = self.get_parameter('fps').value
        camera_info_url = self.get_parameter('camera_info_url').value
        
        # Inicializar cámara
        # LOG ELIMINADO: f"Iniciando cámara USB con ID: {camera_id}"
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Verificar si la cámara se abrió correctamente
        if not self.cap.isOpened():
            self.get_logger().error(f"No se pudo abrir la cámara {camera_id}")
            raise RuntimeError(f"No se pudo abrir la cámara {camera_id}")
        
        # Bridge para convertir entre OpenCV y ROS
        self.bridge = CvBridge()
        
        # Publicadores
        self.image_pub = self.create_publisher(Image, 'image_raw', 10)
        self.camera_info_pub = self.create_publisher(CameraInfo, 'camera_info', 10)
        
        # Camera Info Manager (carga calibración desde YAML)
        self.camera_info_manager = CameraInfoManager(
            self, 
            'usb_camera',
            namespace='',
            url=camera_info_url
        )
        self.camera_info_manager.loadCameraInfo()
        
        # Timer para captura de imágenes
        timer_period = 1.0 / fps
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # LOG ELIMINADO: "Nodo de cámara USB iniciado correctamente"
    
    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("No se pudo capturar frame")
            return
        
        # Convertir BGR a RGB (OpenCV usa BGR, ROS usa RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Crear mensaje de imagen
        image_msg = self.bridge.cv2_to_imgmsg(frame_rgb, encoding='rgb8')
        image_msg.header.stamp = self.get_clock().now().to_msg()
        image_msg.header.frame_id = self.frame_id
        
        # Publicar imagen
        self.image_pub.publish(image_msg)
        
        # Publicar información de cámara (con calibración)
        camera_info_msg = self.camera_info_manager.getCameraInfo()
        camera_info_msg.header = image_msg.header
        self.camera_info_pub.publish(camera_info_msg)
    
    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = USBCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
