#!/usr/bin/env python3
"""
NODO DE DETECCIÓN DE OBJETOS PARA ROS2
Se suscribe a /image_raw, detecta objetos, publica resultados
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from cv_bridge import CvBridge
import cv2
import numpy as np
import json
import time
from pathlib import Path

# Mensajes ROS2
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
from geometry_msgs.msg import Point
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

# Importar nuestro detector
from .robot_vision.robot_detector import RobotDetectorROS

class ObjectDetectorNode(Node):
    def __init__(self):
        super().__init__('object_detector_node')
        
        # Configurar parámetros
        self.declare_parameters(
            namespace='',
            parameters=[
                ('model.yolo', 'yolov8n.pt'),
                ('model.door', 'best.pt'),
                ('confidence_threshold', 0.25),
                ('publish_rate', 2.0),  # Hz
                ('enable_visualization', True),
                ('models_path', '~/robot_educativo_ws/src/robot_vision/models'),
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
        
        self.get_logger().info(f"Modelo YOLO: {yolo_path}")
        if door_path:
            self.get_logger().info(f"Modelo puertas: {door_path}")
        
        # Inicializar detector
        try:
            self.detector = RobotDetectorROS({
                'yolo': yolo_path,
                'door': door_path if door_path and Path(door_path).exists() else None
            })
            self.get_logger().info("✅ Detector inicializado correctamente")
        except Exception as e:
            self.get_logger().error(f"❌ Error inicializando detector: {e}")
            raise
        
        # Bridge para imágenes
        self.bridge = CvBridge()
        
        # QoS para imágenes (best effort para menor latencia)
        image_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # SUSCRIPTORES
        self.image_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            image_qos
        )
        
        # PUBLICADORES
        # 1. Imagen con detecciones (visualización)
        self.detection_image_pub = self.create_publisher(
            Image,
            '/vision/detection_image',
            10
        )
        
        # 2. Detecciones en formato array (para otros nodos)
        self.detections_pub = self.create_publisher(
            String,  # Usaremos JSON por simplicidad
            '/vision/detections',
            10
        )
        
        # 3. Análisis de navegación
        self.navigation_pub = self.create_publisher(
            String,
            '/vision/navigation_analysis',
            10
        )
        
        # 4. Descripción textual (para voz)
        self.description_pub = self.create_publisher(
            String,
            '/vision/scene_description',
            10
        )
        
        # 5. Estadísticas
        self.stats_pub = self.create_publisher(
            String,
            '/vision/detector_stats',
            10
        )
        
        # Timer para publicaciones periódicas (si no hay imagen nueva)
        self.publish_rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / self.publish_rate, self.timer_callback)
        
        # Estado
        self.latest_image = None
        self.latest_detections = []
        self.latest_analysis = {}
        self.last_processed_time = 0
        self.processing = False
        
        self.get_logger().info(" Nodo de detección de objetos iniciado")
        self.get_logger().info(f"   Suscrito a: /image_raw")
        self.get_logger().info(f"   Publicando en: /vision/*")
        self.get_logger().info(f"   Rate: {self.publish_rate} Hz")
    
    def image_callback(self, msg):
        """
        Callback cuando llega nueva imagen de la cámara
        """
        if self.processing:
            return  # Saltar si ya estamos procesando
        
        try:
            self.processing = True
            
            # Convertir mensaje ROS a imagen OpenCV
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
            
            # Guardar imagen para procesamiento
            self.latest_image = cv_image
            
            # Procesar imagen con el detector
            detections, annotated_image, analysis = self.detector.detect_in_image(
                cv_image,
                conf_threshold=self.get_parameter('confidence_threshold').value
            )
            
            # Guardar resultados
            self.latest_detections = detections
            self.latest_analysis = analysis
            self.last_processed_time = time.time()
            
            # Publicar imagen con detecciones
            if self.get_parameter('enable_visualization').value:
                annotated_msg = self.bridge.cv2_to_imgmsg(
                    cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR),
                    encoding='bgr8'
                )
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
            
            # Publicar análisis de navegación
            analysis_msg = String()
            analysis_msg.data = json.dumps(self.latest_analysis)
            self.navigation_pub.publish(analysis_msg)
            
            # Generar y publicar descripción textual
            description = self.detector.describe_scene(self.latest_analysis)
            desc_msg = String()
            desc_msg.data = description
            self.description_pub.publish(desc_msg)
            
            # Publicar estadísticas
            stats = self.detector.get_statistics()
            stats['node_uptime'] = time.time() - self._start_time
            stats_msg = String()
            stats_msg.data = json.dumps(stats)
            self.stats_pub.publish(stats_msg)
            
            # Log cada 30 frames
            if self.detector.frame_count % 30 == 0:
                self.get_logger().info(
                    f"Frame {self.detector.frame_count}: "
                    f"{len(detections)} objetos, "
                    f"{stats.get('fps', 0):.1f} FPS"
                )
            
        except Exception as e:
            self.get_logger().error(f"Error procesando imagen: {e}")
        finally:
            self.processing = False
    
    def timer_callback(self):
        """
        Publica información periódicamente incluso si no hay imágenes nuevas
        """
        if self.latest_analysis and (time.time() - self.last_processed_time < 5.0):
            # Re-publicar última descripción (para voz)
            description = self.detector.describe_scene(self.latest_analysis)
            desc_msg = String()
            desc_msg.data = description
            self.description_pub.publish(desc_msg)
    
    def destroy_node(self):
        self.get_logger().info("Apagando nodo de detección...")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = ObjectDetectorNode()
        node._start_time = time.time()
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
