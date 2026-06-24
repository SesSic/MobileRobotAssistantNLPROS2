#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist, Vector3
import math
import numpy as np
from enum import Enum

class NavigationState(Enum):
    EXPLORE = 1      # Exploración libre
    APPROACH = 2     # Acercamiento controlado
    AVOID = 3        # Evasión de obstáculos
    EMERGENCY_STOP = 4  # Parada de emergencia
    SEARCH = 5       # Búsqueda de camino libre

class NavigationNode(Node):
    def __init__(self):
        super().__init__('navigation_node')
        
        # ============ SUSCRIPTORES Y PUBLICADORES ============
        self.ultrasonic_sub = self.create_subscription(
            Range, 
            'ultrasonic/distance', 
            self.ultrasonic_callback, 
            10
        )
        
        # SUSCRIPTOR IMU
        self.imu_sub = self.create_subscription(
            Vector3,
            '/imu/angle',
            self.imu_callback,
            10
        )
        
        # Estado para IMU
        self.current_yaw = 0.0
        self.target_yaw = 0.0
        self.imu_available = False
        
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # ============ ESTADO DEL ROBOT ============
        self.state = NavigationState.EXPLORE
        self.last_distance = 2.0  # metros
        self.obstacle_detected = False
        
        # Timer principal (10Hz = 100ms)
        self.timer = self.create_timer(0.1, self.control_loop)
        
        # ============ PARÁMETROS DE NAVEGACIÓN ============
        # Distancias de seguridad (metros)
        self.EMERGENCY_DIST = 0.15   # 15cm - PARADA INMEDIATA
        self.AVOID_DIST = 0.35       # 35cm - INICIAR EVASIÓN
        self.SAFE_DIST = 0.50        # 50cm - DISTANCIA SEGURA
        
        # Velocidades (ajustadas para N20 100RPM)
        self.SPEED_NORMAL = 0.18     # m/s - Velocidad crucero
        self.SPEED_CAUTION = 0.10    # m/s - Velocidad precaución
        self.SPEED_SLOW = 0.05       # m/s - Velocidad maniobra
        
        # Velocidades de giro (rad/s)
        self.TURN_SLOW = 1.0         # Giro suave
        self.TURN_FAST = 2.0         # Giro rápido
        self.TURN_SPOT = 3.0         # Giro sobre su propio eje
        
        # ============ CONTADORES Y TIMERS ============
        self.avoid_start_time = None
        self.avoid_duration = 1.5    # 1.5 segundos evadiendo
        self.no_obstacle_counter = 0
        self.consecutive_clears = 0  # Para filtrado de lecturas
        
        # BLOQUE DE LOGS DE INICIO ELIMINADO
    
    def ultrasonic_callback(self, msg):
        """Procesar distancia con filtrado"""
        distance = msg.range
        
        # FILTRO: Ignurar lecturas fuera de rango
        if distance < 0.02 or distance > 4.0:
            return
        
        # FILTRO: Suavizado exponencial
        alpha = 0.3  # Factor de suavizado
        self.last_distance = alpha * distance + (1 - alpha) * self.last_distance
        
        # ============ MÁQUINA DE ESTADOS ============
        if self.last_distance < self.EMERGENCY_DIST:
            # EMERGENCIA - Parada inmediata
            if self.state != NavigationState.EMERGENCY_STOP:
                self.get_logger().error(f" EMERGENCIA! Distancia: {self.last_distance:.3f}m")
                self.state = NavigationState.EMERGENCY_STOP
                self.avoid_start_time = self.get_clock().now()
                
        elif self.last_distance < self.AVOID_DIST:
            # OBSTÁCULO CERCA - Evasión necesaria
            if self.state != NavigationState.AVOID:
                self.get_logger().warn(f" Obstáculo detectado: {self.last_distance:.2f}m")
                self.state = NavigationState.AVOID
                self.avoid_start_time = self.get_clock().now()
                self.consecutive_clears = 0
                
        elif self.last_distance < self.SAFE_DIST:
            # OBSTÁCULO LEJOS - Acercamiento controlado
            if self.state == NavigationState.EXPLORE:
                self.state = NavigationState.APPROACH
                # LOG ELIMINADO: info de acercamiento
        else:
            # LIBRE - Incrementar contador de lecturas libres
            self.consecutive_clears += 1
            
            # Solo cambiar a EXPLORE después de múltiples lecturas libres
            if (self.consecutive_clears > 3 and 
                self.state in [NavigationState.AVOID, NavigationState.APPROACH, NavigationState.SEARCH]):
                self.state = NavigationState.EXPLORE
                # LOG ELIMINADO: info de exploración
    
    def control_loop(self):
        """Lógica principal de control - ejecutada a 10Hz"""
        
        cmd = Twist()
        
        # ============ MÁQUINA DE ESTADOS PRINCIPAL ============
        
        # 1. EMERGENCIA - Parada total
        if self.state == NavigationState.EMERGENCY_STOP:
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            
            # Verificar si podemos salir de emergencia
            if self.last_distance > self.EMERGENCY_DIST + 0.05:  # Histéresis
                self.state = NavigationState.SEARCH
                # LOG ELIMINADO: info de búsqueda
        
        # 2. EVASIÓN - Esquivar obstáculo
        elif self.state == NavigationState.AVOID:
            cmd.linear.x = 0.0  # Primero paramos
            
            # Estrategia de evasión
            elapsed = (self.get_clock().now() - self.avoid_start_time).nanoseconds / 1e9
            
            if elapsed < 0.5:
                # Primero: giro fuerte para alejarse
                cmd.angular.z = self.TURN_FAST
            elif elapsed < 1.0:
                # Segundo: giro más suave
                cmd.angular.z = self.TURN_SLOW
            else:
                # Tercero: ligero avance girando
                cmd.linear.x = self.SPEED_SLOW
                cmd.angular.z = self.TURN_SLOW / 2
            
            # Si ya pasó el tiempo de evasión, buscar camino libre
            if elapsed > self.avoid_duration:
                self.state = NavigationState.SEARCH
        
        # 3. BÚSQUEDA - Girar para encontrar espacio libre
        elif self.state == NavigationState.SEARCH:
            cmd.linear.x = 0.0
            
            # Si tenemos IMU disponible, usar giro preciso
            if self.imu_available:
                # Inicializar giro objetivo (90°)
                if not hasattr(self, 'search_start_yaw'):
                    self.search_start_yaw = self.current_yaw
                    self.target_yaw = self.current_yaw + 90
                    # Normalizar target a [-180, 180]
                    self.target_yaw = (self.target_yaw + 180) % 360 - 180
                    # LOG ELIMINADO: info de giro
                
                # Calcular error
                error = self.target_yaw - self.current_yaw
                error = (error + 180) % 360 - 180
                
                if abs(error) < 5:  # 5° de tolerancia
                    # Giro completado
                    delattr(self, 'search_start_yaw')
                    self.state = NavigationState.EXPLORE
                    # LOG ELIMINADO: info de giro completado
                else:
                    # Seguir girando
                    cmd.angular.z = 0.3 if error > 0 else -0.3
            else:
                # Fallback: giro por tiempo (sin IMU)
                cmd.angular.z = self.TURN_SPOT * 0.7
                # Salir después de 2 segundos
                if not hasattr(self, 'search_start_time'):
                    self.search_start_time = self.get_clock().now()
                else:
                    elapsed = (self.get_clock().now() - self.search_start_time).nanoseconds / 1e9
                    if elapsed > 2.0:
                        delattr(self, 'search_start_time')
                        self.state = NavigationState.EXPLORE
                        # LOG ELIMINADO: info de giro por tiempo
        
        # 4. ACERCAMIENTO - Avanzar con precaución
        elif self.state == NavigationState.APPROACH:
            # Avanzar lento hacia el obstáculo (para mejor detección)
            cmd.linear.x = self.SPEED_CAUTION
            cmd.angular.z = 0.0
            
            # Si nos acercamos demasiado, cambiar a evasión
            if self.last_distance < self.AVOID_DIST:
                self.state = NavigationState.AVOID
                self.avoid_start_time = self.get_clock().now()
        
        # 5. EXPLORACIÓN - Avanzar normalmente
        elif self.state == NavigationState.EXPLORE:
            cmd.linear.x = self.SPEED_NORMAL
            # Pequeño zigzag para exploración más eficiente
            cmd.angular.z = math.sin(self.get_clock().now().nanoseconds / 5e8) * 0.1
        
        # ============ PUBLICAR COMANDO ============
        self.cmd_pub.publish(cmd)
        
        # ============ LOGGING ELIMINADO (periódico cada 1s) ============
        # BLOQUE ELIMINADO - Ya no se publica estado cada segundo
    
    def imu_callback(self, msg):
        """Actualiza orientación desde IMU"""
        self.current_yaw = msg.z  # Ángulo en grados
        self.imu_available = True

        # Verificar si estamos en un giro con objetivo
        if hasattr(self, 'target_yaw'):
            error = self.target_yaw - self.current_yaw
            # Normalizar a [-180, 180]
            error = (error + 180) % 360 - 180
            
            if abs(error) < 5:  # 5° de tolerancia
                # LOG ELIMINADO: info de giro completado
                self.target_yaw = self.current_yaw
    
    def destroy_node(self):
        """Limpieza al cerrar"""
        # Publicar comando de parada
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)
        
        # LOG ELIMINADO: navegación detenida
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = NavigationNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass  # LOG ELIMINADO: interrupción por usuario
    except Exception as e:
        node.get_logger().error(f" Error fatal: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
