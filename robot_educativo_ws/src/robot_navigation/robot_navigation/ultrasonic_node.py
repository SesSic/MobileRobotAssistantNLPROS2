#!/usr/bin/env python3
"""
NODO ULTRASÓNICO HC-SR04 - Publica distancia en Float32
Para integración con ObjectFollowerNode
Autor: Sebastián Aucapiña
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import RPi.GPIO as GPIO
import time

class UltrasonicNode(Node):
    def __init__(self):
        super().__init__('ultrasonic_node')
        
        # Configuración GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.TRIG = 23
        self.ECHO = 24
        
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.output(self.TRIG, False)
        
        # Publicador - AHORA EN FLOAT32
        self.publisher = self.create_publisher(
            Float32,
            '/ultrasonic/distance',
            10
        )
        
        # Timer (10Hz)
        self.timer = self.create_timer(0.1, self.measure_distance)
        
        # Estadísticas
        self.measurement_count = 0
        
        # BLOQUE DE LOGS DE INICIO ELIMINADO
    
    def measure_distance(self):
        """Mide distancia y publica como Float32 (metros)"""
        try:
            # Asegurar trigger en bajo
            GPIO.output(self.TRIG, False)
            time.sleep(0.00005)  # 50µs
            
            # Enviar pulso de 10µs
            GPIO.output(self.TRIG, True)
            time.sleep(0.00001)   # 10µs
            GPIO.output(self.TRIG, False)
            
            # Timeout para evitar bloqueos
            timeout = time.time() + 0.1  # 100ms timeout
            
            # Esperar ECHO en alto
            while GPIO.input(self.ECHO) == 0:
                if time.time() > timeout:
                    return
                pulse_start = time.time()
            
            # Esperar ECHO en bajo
            while GPIO.input(self.ECHO) == 1:
                if time.time() > timeout:
                    return
                pulse_end = time.time()
            
            # Calcular distancia
            pulse_duration = pulse_end - pulse_start
            distance_cm = (pulse_duration * 34300) / 2
            
            # Filtrar valores fuera de rango
            if distance_cm < 2 or distance_cm > 400:
                return
            
            # Convertir a metros
            distance_m = distance_cm / 100.0
            
            # Publicar como Float32
            msg = Float32()
            msg.data = distance_m
            self.publisher.publish(msg)
            
            # LOG ELIMINADO: Logging periódico cada 3 segundos
            
            # Alerta si hay obstáculo cercano (MANTENER)
            if distance_m < 0.3:
                self.get_logger().warn(f" CUIDADO: {distance_m:.2f}m")
                
        except Exception as e:
            self.get_logger().error(f" Error: {e}")
    
    def destroy_node(self):
        """Limpieza de GPIO"""
        GPIO.cleanup()
        # LOG ELIMINADO: " GPIO cleaned up"
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass  # LOG ELIMINADO: "\n Ultrasonido detenido"
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()