#!/usr/bin/env python3
"""
 NODO SIMPLIFICADO DE DETECCIÓN DE OBJETOS PARA ROS2
Sin dependencia de vision_msgs
"""

import rclpy
from rclpy.node import Node
from cv_bridge import CvBridge
import cv2
import json
import time
from pathlib import Path

# Mensajes ROS2 básicos
from sensor_msgs.msg import Image
from std_msgs.msg import String

# Importar nuestro detector
from .robot_detector import RobotDetectorROS

class ObjectDetectorNode(Node):
    def __init__(self):
        super().__init__('object_detector_node')
        
        # Configurar parámetros
        self.declare_parameters(
            namespace='',
            parameters=[
                ('model.yolo', 'yolov8n.pt'),
                ('model.door', ''),
                ('confidence_threshold', 0.25),
                ('publish_rate', 2.0),  # Hz
                ('enable_visualization', True),
                ('models_path', '/home/sessic/robot_educativo_ws/src/robot_vision/models'),
            ]
        )
        
        # Obtener parámetros
        yolo_path = self.get_parameter('model.yolo').value
        door_path = self.get_parameter('model.door').value
        models_path = Path(self.get_parameter('models_path').value).expanduser()
        
        # Construir rutas completas
        if not Path(yolo_path).is_absolute():
            yolo_path = str(models_path / yolo_path)
        
        if door_path and not Path(door_path).is_absolute():
            door_path = str(models_path / door_path)
        
        # LOGS ELIMINADOS: Información de rutas de modelos
        
        # Inicializar detector
        try:
            self.detector = RobotDetectorROS({
                'yolo': yolo_path,
                'door': door_path if door_path and Path(door_path).exists() else None
            })
            # LOG ELIMINADO: " Detector inicializado correctamente"
        except Exception as e:
            self.get_logger().error(f" Error inicializando detector: {e}")
            raise
        
        # Bridge para imágenes
        self.bridge = CvBridge()
        
        # SUSCRIPTORES
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',  # Cambié a coincidir con remapping
            self.image_callback,
            10
        )
        
        # PUBLICADORES
        # 1. Imagen con detecciones
        self.detection_image_pub = self.create_publisher(
            Image,
            '/vision/detection_image',
            10
        )
        
        # 2. Detecciones en JSON
        self.detections_pub = self.create_publisher(
            String,
            '/vision/detections',
            10
        )
        
        # 3. Descripción textual (para voz)
        self.description_pub = self.create_publisher(
            String,
            '/vision/scene_description',
            10
        )
        
        # Estado
        self.latest_image = None
        self.latest_detections = []
        self.latest_analysis = {}
        self.processing = False
        
        # LOGS DE INICIO ELIMINADOS
    
    def image_callback(self, msg):
        """Callback cuando llega nueva imagen"""
        if self.processing:
            return
        
        try:
            self.processing = True
            
            # Convertir mensaje ROS a imagen OpenCV
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
            
            # Procesar imagen con el detector
            detections, annotated_image, analysis = self.detector.detect_in_image(
                cv_image,
                conf_threshold=self.get_parameter('confidence_threshold').value
            )
            
            # Guardar resultados
            self.latest_detections = detections
            self.latest_analysis = analysis
            
            # Publicar imagen con detecciones (si está habilitado)
            if self.get_parameter('enable_visualization').value:
                # Convertir RGB a BGR para OpenCV
                annotated_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
                annotated_msg = self.bridge.cv2_to_imgmsg(annotated_bgr, encoding='bgr8')
                annotated_msg.header = msg.header
                self.detection_image_pub.publish(annotated_msg)
            
            # Publicar detecciones como JSON
            detections_json = {
                'timestamp': time.time(),
                'detections': self.latest_detections,
                'image_size': {
                    'width': cv_image.shape[1],
                    'height': cv_image.shape[0]
                }
            }
            
            detections_msg = String()
            detections_msg.data = json.dumps(detections_json)
            self.detections_pub.publish(detections_msg)
            
            # Generar y publicar descripción textual
            description = self.detector.describe_scene(analysis)
            desc_msg = String()
            desc_msg.data = description
            self.description_pub.publish(desc_msg)
            
            # LOG ELIMINADO: Mensaje periódico cada 30 frames
            
        except Exception as e:
            self.get_logger().error(f"Error procesando imagen: {e}")
        finally:
            self.processing = False
    
    def destroy_node(self):
        # LOG ELIMINADO: "Apagando nodo de detección..."
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = ObjectDetectorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
