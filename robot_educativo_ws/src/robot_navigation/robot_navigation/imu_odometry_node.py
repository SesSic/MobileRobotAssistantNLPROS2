#!/usr/bin/env python3
"""
NODO IMU MPU6050 PARA ROS2
Publica datos crudos y orientación
Autor: Sebastián Aucapiña
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField
from geometry_msgs.msg import Vector3, Quaternion
from std_msgs.msg import Header
import math
import smbus2
import time
import numpy as np

class IMUOdometryNode(Node):
    def __init__(self):
        super().__init__('imu_node')
        
        # Parámetros
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('device_address', 0x68)
        self.declare_parameter('publish_rate', 50)  # Hz
        self.declare_parameter('calibration_time', 2.0)  # segundos
        
        # Obtener parámetros
        self.frame_id = self.get_parameter('frame_id').value
        self.bus_num = self.get_parameter('i2c_bus').value
        self.device_addr = self.get_parameter('device_address').value
        self.rate = self.get_parameter('publish_rate').value
        
        # Inicializar I2C
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            # LOG ELIMINADO: self.get_logger().info(f"I2C bus {self.bus_num} abierto")
        except Exception as e:
            self.get_logger().error(f"No se pudo abrir I2C: {e}")
            raise
        
        # Inicializar MPU6050
        self.init_mpu6050()
        
        # Calibrar
        # LOGS ELIMINADOS: "Calibrando IMU. NO MOVER..." y "Calibración completada"
        self.calibrate()
        
        # Estado
        self.gyro_bias = np.array([0.0, 0.0, 0.0])
        self.accel_bias = np.array([0.0, 0.0, 0.0])
        self.angle = np.array([0.0, 0.0, 0.0])  # roll, pitch, yaw
        self.last_time = time.time()
        
        # Publicadores
        self.imu_pub = self.create_publisher(Imu, '/imu/data_raw', 10)
        self.mag_pub = self.create_publisher(MagneticField, '/imu/mag', 10)
        self.angle_pub = self.create_publisher(Vector3, '/imu/angle', 10)
        
        # Timer
        timer_period = 1.0 / self.rate
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # LOGS ELIMINADOS: "✅ Nodo IMU iniciado" y "Publicando en /imu/data_raw @ ..."
    
    def init_mpu6050(self):
        """Inicializa el MPU6050 con configuración estándar"""
        try:
            # Despertar el MPU6050 (escribir 0 en registro 0x6B)
            self.bus.write_byte_data(self.device_addr, 0x6B, 0)
            
            # Configurar acelerómetro: ±2g
            self.bus.write_byte_data(self.device_addr, 0x1C, 0x00)
            
            # Configurar giroscopio: ±250°/s
            self.bus.write_byte_data(self.device_addr, 0x1B, 0x00)
            
            # Configurar filtro pasa bajos: 44Hz
            self.bus.write_byte_data(self.device_addr, 0x1A, 0x03)
            
            # LOG ELIMINADO: self.get_logger().info("MPU6050 configurado correctamente")
            
        except Exception as e:
            self.get_logger().error(f"Error configurando MPU6050: {e}")
            raise
    
    def read_raw_values(self):
        """Lee valores crudos del MPU6050"""
        try:
            # Leer 14 registros desde 0x3B (ACCEL_XOUT_H)
            data = self.bus.read_i2c_block_data(self.device_addr, 0x3B, 14)
            
            # Convertir a enteros de 16 bits
            accel_x = (data[0] << 8) | data[1]
            accel_y = (data[2] << 8) | data[3]
            accel_z = (data[4] << 8) | data[5]
            temp = (data[6] << 8) | data[7]
            gyro_x = (data[8] << 8) | data[9]
            gyro_y = (data[10] << 8) | data[11]
            gyro_z = (data[12] << 8) | data[13]
            
            # Convertir a complemento a 2
            accel_x = accel_x - 65536 if accel_x > 32768 else accel_x
            accel_y = accel_y - 65536 if accel_y > 32768 else accel_y
            accel_z = accel_z - 65536 if accel_z > 32768 else accel_z
            gyro_x = gyro_x - 65536 if gyro_x > 32768 else gyro_x
            gyro_y = gyro_y - 65536 if gyro_y > 32768 else gyro_y
            gyro_z = gyro_z - 65536 if gyro_z > 32768 else gyro_z
            
            return {
                'accel': np.array([accel_x, accel_y, accel_z]),
                'gyro': np.array([gyro_x, gyro_y, gyro_z]),
                'temp': temp / 340.0 + 36.53  # Temperatura en °C
            }
            
        except Exception as e:
            self.get_logger().error(f"Error leyendo MPU6050: {e}")
            return None
    
    def calibrate(self):
        """Calibración: calcula bias de giroscopio y acelerómetro"""
        cal_time = self.get_parameter('calibration_time').value
        samples = int(cal_time * 100)  # ~100Hz
        gyro_sum = np.array([0.0, 0.0, 0.0])
        accel_sum = np.array([0.0, 0.0, 0.0])
        count = 0
        
        for _ in range(samples):
            data = self.read_raw_values()
            if data:
                gyro_sum += data['gyro']
                accel_sum += data['accel']
                count += 1
            time.sleep(0.01)
        
        if count > 0:
            self.gyro_bias = gyro_sum / count
            self.accel_bias = accel_sum / count
            
            # El acelerómetro debería leer [0, 0, 16384] en reposo (1g)
            self.accel_bias[2] -= 16384  # Restar 1g en Z
            
            # LOGS ELIMINADOS: "Gyro bias: ..." y "Accel bias: ..."
    
    def compute_angle_from_accel(self, accel):
        """Calcula roll y pitch desde acelerómetro"""
        accel_corrected = accel - self.accel_bias
        
        roll = math.atan2(accel_corrected[1], accel_corrected[2])
        pitch = math.atan2(-accel_corrected[0], 
                          math.sqrt(accel_corrected[1]**2 + accel_corrected[2]**2))
        
        return roll, pitch
    
    def timer_callback(self):
        """Callback principal: lee y publica datos IMU"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Leer datos
        data = self.read_raw_values()
        if not data:
            return
        
        # Aplicar bias
        gyro = data['gyro'] - self.gyro_bias
        accel = data['accel'] - self.accel_bias
        
        # Convertir a unidades físicas
        # Acelerómetro: 16384 LSB/g → m/s²
        accel_ms2 = accel * 9.81 / 16384.0
        
        # Giroscopio: 131 LSB/°/s → rad/s
        gyro_rad = gyro * (math.pi / 180.0) / 131.0
        
        # Calcular ángulos
        roll_acc, pitch_acc = self.compute_angle_from_accel(data['accel'])
        
        # Integración simple del giroscopio (yaw)
        self.angle[2] += gyro_rad[2] * dt
        
        # Filtro complementario para roll y pitch
        alpha = 0.98
        self.angle[0] = alpha * (self.angle[0] + gyro_rad[0] * dt) + (1 - alpha) * roll_acc
        self.angle[1] = alpha * (self.angle[1] + gyro_rad[1] * dt) + (1 - alpha) * pitch_acc
        
        # --- PUBLICAR MENSAJE IMU ---
        imu_msg = Imu()
        imu_msg.header = Header()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
        imu_msg.header.frame_id = self.frame_id
        
        # Aceleración
        imu_msg.linear_acceleration.x = accel_ms2[0]
        imu_msg.linear_acceleration.y = accel_ms2[1]
        imu_msg.linear_acceleration.z = accel_ms2[2]
        
        # Velocidad angular
        imu_msg.angular_velocity.x = gyro_rad[0]
        imu_msg.angular_velocity.y = gyro_rad[1]
        imu_msg.angular_velocity.z = gyro_rad[2]
        
        # Orientación (como cuaternión)
        quat = self.euler_to_quaternion(self.angle[0], self.angle[1], self.angle[2])
        imu_msg.orientation.x = quat[0]
        imu_msg.orientation.y = quat[1]
        imu_msg.orientation.z = quat[2]
        imu_msg.orientation.w = quat[3]
        
        # Covarianzas (valores por defecto)
        imu_msg.orientation_covariance[0] = 0.01
        imu_msg.orientation_covariance[4] = 0.01
        imu_msg.orientation_covariance[8] = 0.01
        
        imu_msg.angular_velocity_covariance[0] = 0.01
        imu_msg.angular_velocity_covariance[4] = 0.01
        imu_msg.angular_velocity_covariance[8] = 0.01
        
        imu_msg.linear_acceleration_covariance[0] = 0.01
        imu_msg.linear_acceleration_covariance[4] = 0.01
        imu_msg.linear_acceleration_covariance[8] = 0.01
        
        self.imu_pub.publish(imu_msg)
        
        # Publicar ángulos en grados (para debug)
        angle_msg = Vector3()
        angle_msg.x = math.degrees(self.angle[0])  # roll
        angle_msg.y = math.degrees(self.angle[1])  # pitch
        angle_msg.z = math.degrees(self.angle[2])  # yaw
        self.angle_pub.publish(angle_msg)
        
        # LOG ELIMINADO: Mensaje periódico cada 10 segundos
        """
        if int(self.rate * 10) % self.rate == 0:
            self.get_logger().info(
                f"IMU: roll={angle_msg.x:.1f}°, pitch={angle_msg.y:.1f}°, yaw={angle_msg.z:.1f}°"
            )
        """
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """Convierte ángulos de Euler a cuaternión"""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        q = [0.0, 0.0, 0.0, 0.0]
        q[0] = sr * cp * cy - cr * sp * sy  # x
        q[1] = cr * sp * cy + sr * cp * sy  # y
        q[2] = cr * cp * sy - sr * sp * cy  # z
        q[3] = cr * cp * cy + sr * sp * sy  # w
        
        return q

def main(args=None):
    rclpy.init(args=args)
    node = IMUOdometryNode()  # Nota: la clase se llama IMUOdometryNode, no MPU6050Node
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()