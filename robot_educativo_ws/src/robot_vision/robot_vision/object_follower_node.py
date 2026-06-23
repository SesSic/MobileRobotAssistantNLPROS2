#!/usr/bin/env python3
"""
NODO DE SEGUIMIENTO DE OBJETOS - MODIFICADO PARA USAR MEMORIA VISUAL
Versión: No se activa solo, espera comando explícito
Autor: Sebastián Aucapiña
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import String, Float32
import json
import math
import time

class ObjectFollowerNode(Node):
    def __init__(self):
        super().__init__('object_follower_node')
        
        # ============ PARÁMETROS ============
        self.declare_parameters(
            namespace='',
            parameters=[
                ('linear_speed', 0.12),        # m/s
                ('angular_speed', 1.5),       # rad/s
                ('target_distance', 0.8),       # Distancia deseada
                ('stop_distance', 0.4),         # Distancia para detenerse
                ('angle_threshold', 0.2),       # rad (~11 grados)
                ('search_timeout', 5.0),        # segundos buscando antes de rendirse
                ('max_follow_time', 30.0),       # tiempo máximo siguiendo
            ]
        )
        
        # ============ ESTADO ============
        self.active = False                      # ¿Está siguiendo?
        self.target_object = None                 # Objeto a seguir (ej: "puerta")
        self.target_data = None                   # Datos del objeto (coordenadas)
        self.follow_start_time = None              # Cuándo empezó a seguir
        
        # Últimas detecciones (para usar cuando llega comando)
        self.last_detections = None
        self.last_detections_time = 0
        self.image_width = 640
        self.image_height = 480
        
        # ============ ESTADO IMU ============
        self.current_yaw = 0.0
        self.target_yaw = 0.0
        self.imu_available = False
        self.imu_turn_active = False
        
        # Distancia ultrasónica (seguridad)
        self.ultrasonic_distance = 999.0
        
        # ============ SUSCRIPTORES ============
        # 1. Escuchar target desde voz (NUEVO)
        self.target_sub = self.create_subscription(
            String,
            '/vision/follower/target',
            self.target_callback,
            10
        )
        
        # 2. NUEVO: Escuchar STOP desde voz
        self.stop_sub = self.create_subscription(
	    String,
	    '/vision/follower/stop',
	    self.stop_callback,
	    10
	)

        
        # 2. Detecciones de visión (para obtener coordenadas)
        self.detections_sub = self.create_subscription(
            String,
            '/vision/detections',
            self.detections_callback,
            10
        )
        
        # 3. Distancia ultrasónica
        self.ultrasonic_sub = self.create_subscription(
            Float32,
            '/ultrasonic/distance',
            self.ultrasonic_callback,
            10
        )
        
        # 4. IMU (opcional)
        self.imu_sub = self.create_subscription(
            Vector3,
            '/imu/angle',
            self.imu_callback,
            10
        )
        
        # ============ PUBLICADORES ============
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )
        
        self.status_pub = self.create_publisher(
            String,
            '/follower/status',
            10
        )
        
        # ============ TIMER DE CONTROL ============
        self.control_timer = self.create_timer(0.1, self.control_loop)  # 10Hz
        
        # LOGS DE INICIO ELIMINADOS
    
    # ============ CALLBACKS ============
    
    def target_callback(self, msg):
        """
        NUEVO: Recibe objetivo desde voz
        Ejemplo: "puerta", "persona", "silla"
        """
        target = msg.data.lower().strip()
        
        # LOG ELIMINADO: f" Objetivo recibido: '{target}'"
        
        # Verificar si tenemos detecciones recientes
        tiempo_actual = time.time()
        if tiempo_actual - self.last_detections_time > 10.0:  # 10 segundos máximo
            self.get_logger().warning(" No hay detecciones recientes (más de 10s)")
            self.publicar_estado(f"error:sin_detecciones")
            return
        
        if not self.last_detections:
            self.get_logger().warning(" No hay detecciones guardadas")
            self.publicar_estado(f"error:sin_detecciones")
            return
        
        # Buscar el objeto en las últimas detecciones
        objeto_encontrado = self.buscar_objeto_en_detecciones(target)
        
        if objeto_encontrado:
            self.target_object = target
            self.target_data = objeto_encontrado
            self.active = True
            self.follow_start_time = tiempo_actual
            self.imu_turn_active = False
            
            # LOGS DE INICIO DE SEGUIMIENTO ELIMINADOS
            
            self.publicar_estado(f"siguiendo:{target}")
        else:
            self.get_logger().warning(f" No se encontró '{target}' en las últimas detecciones")
            # LOG ELIMINADO: Lista de objetos disponibles
            self.publicar_estado(f"error:objeto_no_encontrado:{target}")
    
    def detections_callback(self, msg):
        """Guarda las últimas detecciones para cuando llegue un comando"""
        try:
            data = json.loads(msg.data)
            self.last_detections = data
            self.last_detections_time = time.time()
            
            # Guardar dimensiones de imagen
            self.image_width = data.get('image_size', {}).get('width', 640)
            self.image_height = data.get('image_size', {}).get('height', 480)
            
        except Exception as e:
            self.get_logger().error(f"Error guardando detecciones: {e}")
    
    def buscar_objeto_en_detecciones(self, target):
        """
        Busca el objeto target en las últimas detecciones
        Retorna el mejor candidato (más cercano o con mayor confianza)
        """
        if not self.last_detections:
            return None
        
        detections = self.last_detections.get('detections', [])
        candidatos = []
        
        for det in detections:
            obj_class = det.get('class', '').lower()
            
            # Coincidencia exacta o parcial
            if (target in obj_class or obj_class in target or
                target == obj_class or
                # Plurales
                (target + 's' == obj_class) or
                (obj_class + 's' == target) or
                # Inglés
                (target == 'person' and obj_class == 'persona') or
                (target == 'door' and obj_class == 'puerta')):
                
                # Extraer información
                bbox = det.get('bbox', [0, 0, 0, 0])
                x1, y1, x2, y2 = bbox
                
                # Calcular centro y ángulo
                center_x = (x1 + x2) / 2
                
                # Ángulo (FOV 62°)
                FOV = 62 * (math.pi / 180)
                pixel_angle = FOV / self.image_width
                angle = (center_x - self.image_width/2) * pixel_angle
                
                # Estimar distancia
                bbox_height = y2 - y1
                if bbox_height > 0:
                    # Fórmula empírica
                    distance = (1.2 * self.image_height) / (bbox_height * 0.9)
                    distance = min(max(distance, 0.3), 5.0)
                else:
                    distance = 999.0
                
                candidatos.append({
                    'class': obj_class,
                    'distance': distance,
                    'angle': angle,
                    'confidence': det.get('confidence', 0),
                    'bbox': bbox
                })
        
        if not candidatos:
            return None
        
        # Ordenar por distancia (más cercano primero)
        candidatos.sort(key=lambda x: x['distance'])
        return candidatos[0]
    
    def obtener_lista_objetos(self):
        """Devuelve lista de objetos disponibles en últimas detecciones"""
        if not self.last_detections:
            return "ninguno"
        
        objetos = set()
        for det in self.last_detections.get('detections', []):
            objetos.add(det.get('class', ''))
        
        return ', '.join(objetos)
    
    def ultrasonic_callback(self, msg):
        """Actualiza distancia ultrasónica"""
        self.ultrasonic_distance = msg.data
    
    def imu_callback(self, msg):
        """Actualiza orientación desde IMU"""
        self.current_yaw = msg.z
        self.imu_available = True
        
    def stop_callback(self, msg):
        """Detiene el seguimiento inmediatamente"""
        if msg.data == "stop":
            # LOG ELIMINADO: " Comando STOP recibido desde voz"
            self.detener_seguimiento()
    
    # ============ BUCLE PRINCIPAL DE CONTROL ============
    
    def control_loop(self):
        """Bucle principal - Solo activo si hay objetivo"""
        if not self.active or not self.target_data:
            return
        
        # Verificar timeout de seguimiento
        max_time = self.get_parameter('max_follow_time').value
        if time.time() - self.follow_start_time > max_time:
            # LOG ELIMINADO: f" Tiempo máximo de seguimiento alcanzado ({max_time}s)"
            self.detener_seguimiento()
            return
        
        # Verificar obstáculo cercano
        if self.ultrasonic_distance < 0.25:  # 25cm
            self.get_logger().warn(f" Obstáculo detectado: {self.ultrasonic_distance:.2f}m")
            self.publicar_velocidad(0.0, 0.0)  # Parar
            return
        
        # Obtener datos del objetivo
        distance = self.target_data['distance']
        angle = self.target_data['angle']
        angle_deg = math.degrees(angle)
        
        # LOG ELIMINADO: Log periódico cada ~2 segundos
        
        # ============ CONTROL ANGULAR ============
        twist = Twist()
        angle_threshold = self.get_parameter('angle_threshold').value
        
        # Control proporcional del ángulo
        if abs(angle) > angle_threshold:
            twist.angular.z = -angle * 0.5  # Ganancia
            max_angular = self.get_parameter('angular_speed').value
            twist.angular.z = max(min(twist.angular.z, max_angular), -max_angular)
        
        # ============ CONTROL LINEAL ============
        target_dist = self.get_parameter('target_distance').value
        stop_dist = self.get_parameter('stop_distance').value
        
        # Solo avanzar si estamos alineados
        if abs(angle) < angle_threshold * 1.5:
            if distance > target_dist:
                # Acercarse
                twist.linear.x = self.get_parameter('linear_speed').value
                
                # Reducir velocidad al acercarse
                if distance < target_dist * 1.5:
                    twist.linear.x *= 0.6
                
            elif distance < stop_dist:
                # Llegamos al objetivo
                # LOG ELIMINADO: f" Llegué a {self.target_object}"
                self.publicar_estado(f"llegue:{self.target_object}")
                self.detener_seguimiento()
                return
        else:
            # Demasiado angulado, priorizar giro
            twist.linear.x = 0.0
        
        # Publicar comando
        self.cmd_vel_pub.publish(twist)
    
    def publicar_velocidad(self, linear, angular):
        """Publica comando de velocidad"""
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
    
    def publicar_estado(self, estado):
        """Publica estado para monitoreo"""
        msg = String()
        msg.data = estado
        self.status_pub.publish(msg)
    
    def detener_seguimiento(self):
        """Detiene el seguimiento y limpia estado"""
        self.active = False
        self.target_object = None
        self.target_data = None
        
        # Publicar parada
        self.publicar_velocidad(0.0, 0.0)
        
        # LOG ELIMINADO: " Seguimiento detenido"
        self.publicar_estado("detenido")


def main(args=None):
    rclpy.init(args=args)
    node = ObjectFollowerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass  # LOG ELIMINADO: "\n Seguimiento terminado por usuario"
    finally:
        # Asegurar parada
        twist = Twist()
        node.cmd_vel_pub.publish(twist)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()