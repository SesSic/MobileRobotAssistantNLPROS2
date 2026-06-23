#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import RPi.GPIO as GPIO
import time
import math

class MotorController(Node):
    def __init__(self):
        super().__init__('motor_controller')
        
        # ============ CORRECCIÓN DE PINES ============
        # Basado en tus pruebas:
        # - Motor A (M1) = Derecho ✓
        # - Motor B (M2) = Izquierdo (con direcciones invertidas)
        
        # Motor DERECHO (A) - PWMA, AIN1, AIN2
        self.PWMA = 13   # PWM motor derecho
        self.AIN1 = 19   # Dirección derecho 1
        self.AIN2 = 26   # Dirección derecho 2
        
        # Motor IZQUIERDO (B) - PWMB, BIN1, BIN2  
        self.PWMB = 12   # PWM motor izquierdo
        self.BIN1 = 16   # Dirección izquierdo 1
        self.BIN2 = 20   # Dirección izquierdo 2
        
        # IMPORTANTE: STBY va directo a 3.3V, NO a GPIO
        # No configuramos pin para STBY
        
        # Configurar GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configurar SOLO los pines que controlamos
        output_pins = [self.PWMA, self.AIN1, self.AIN2, 
                       self.PWMB, self.BIN1, self.BIN2]
            
        for pin in output_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)  # Inicializar en LOW
        
        # Configurar PWM (100Hz frecuencia)
        self.pwm_right = GPIO.PWM(self.PWMA, 100)  # Motor derecho
        self.pwm_left = GPIO.PWM(self.PWMB, 100)   # Motor izquierdo
        self.pwm_right.start(0)
        self.pwm_left.start(0)
        
        # NO configuramos STBY - va directo a 3.3V
        
        # Suscriptor a comandos de velocidad
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        # BLOQUE DE LOGS ELIMINADO (inicio)
    
    def set_motor_right(self, speed):
        """Controlar motor derecho (antes Motor A)"""
        # speed: -100 a 100 (negativo = reversa)
        if speed >= 0:
            # Adelante
            GPIO.output(self.AIN1, GPIO.LOW)
            GPIO.output(self.AIN2, GPIO.HIGH)
        else:
            # Atrás
            GPIO.output(self.AIN1, GPIO.HIGH)
            GPIO.output(self.AIN2, GPIO.LOW)
        
        # Aplicar PWM (valor absoluto, limitado a 0-100)
        duty = min(100, max(0, abs(speed)))
        self.pwm_right.ChangeDutyCycle(duty)
    
    def set_motor_left(self, speed):
        """Controlar motor izquierdo (antes Motor B) - CON DIRECCIONES CORREGIDAS"""
        # speed: -100 a 100 (negativo = reversa)
        
        # ============ CORRECCIÓN IMPORTANTE ============
        # Según pruebas: Motor B tiene direcciones invertidas
        # Intercambiamos HIGH/LOW para BIN1 y BIN2
        
        if speed >= 0:
            # ADELANTE - Configuración invertida
            GPIO.output(self.BIN1, GPIO.HIGH)   # Normal sería HIGH
            GPIO.output(self.BIN2, GPIO.LOW)    # Normal sería LOW
        else:
            # ATRÁS - Configuración invertida
            GPIO.output(self.BIN1, GPIO.LOW)    # Normal sería LOW
            GPIO.output(self.BIN2, GPIO.HIGH)   # Normal sería HIGH
        
        # Aplicar PWM (valor absoluto, limitado a 0-100)
        duty = min(100, max(0, abs(speed)))
        self.pwm_left.ChangeDutyCycle(duty)
    
    def cmd_vel_callback(self, msg):
        try:
            # Parámetros del robot (¡tus medidas reales!)
            wheel_radius = 0.0215      # 43mm diámetro
            wheel_separation = 0.10     # 10cm entre ruedas
           
            # Velocidades deseadas
            linear = msg.linear.x
            angular = msg.angular.z
            
            # Modelo diferencial
            v_left = linear - (angular * wheel_separation / 2)
            v_right = linear + (angular * wheel_separation / 2)
            
            # Convertir a velocidad angular de las ruedas
            w_left = v_left / wheel_radius
            w_right = v_right / wheel_radius
        
            # ============ CALIBRACIÓN EMPÍRICA ============
            # Este valor ajusta cuánto PWM corresponde a cada rad/s
            # ANTES: max_rad_s = 10.47 (muy optimista)
            # AHORA: Valor calibrado experimentalmente
            max_rad_s = 7.5  # Reduce este valor para más giro
        
            # Calcular PWM
            left_pwm_raw = (w_left / max_rad_s) * 100.0
            right_pwm_raw = (w_right / max_rad_s) * 100.0
        
            # Limitar
            left_speed = max(-100.0, min(100.0, left_pwm_raw))
            right_speed = max(-100.0, min(100.0, right_pwm_raw))
        
            self.set_motor_left(left_speed)
            self.set_motor_right(right_speed)
                
        except Exception as e:
            self.get_logger().error(f" Error en cmd_vel: {e}")
    
    def stop_motors(self):
        """Detener motores"""
        self.set_motor_left(0)
        self.set_motor_right(0)
        # LOG ELIMINADO: " Motores detenidos"
    
    def destroy_node(self):
        """Limpieza"""
        self.stop_motors()
        self.pwm_left.stop()
        self.pwm_right.stop()
        GPIO.cleanup()
        # LOG ELIMINADO: " GPIO limpio, nodo destruido"
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = MotorController()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass  # LOG ELIMINADO: " Interrupción por teclado"
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()