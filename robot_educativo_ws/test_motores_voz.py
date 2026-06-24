#!/usr/bin/env python3
"""
Script para probar SOLO los motores con comandos de voz
- Publica en /cmd_vel (Twist) que tu motor_controller ya escucha
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import String
import time
import threading
import subprocess
import json
import queue
import os
import re
from vosk import Model, KaldiRecognizer
import pyaudio

class VoiceMotorTest(Node):
    def __init__(self):
        super().__init__('voice_motor_test')
        
        # Configuración
        self.keyword = "robot"
        self.mic_device = "hw:1,0"
        self.speaker_device = "plughw:2,0"
        self.sample_rate = 16000
        
        # Publicador ROS2 (el mismo que escucha tu motor_controller)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Estado
        self.is_listening = True
        self.audio_queue = queue.Queue()
        
        self.get_logger().info("=" * 50)
        self.get_logger().info(" PRUEBA DE MOTORES POR VOZ")
        self.get_logger().info("=" * 50)
        
        self.init_vosk()
        self.init_audio()
        
        self.get_logger().info("\n Comandos disponibles:")
        self.get_logger().info("   • 'Robot adelante' - Avanza 2 seg")
        self.get_logger().info("   • 'Robot atrás' - Retrocede 2 seg")
        self.get_logger().info("   • 'Robot izquierda' - Gira izquierda")
        self.get_logger().info("   • 'Robot derecha' - Gira derecha")
        self.get_logger().info("   • 'Robot detente' - Para motores")
        self.get_logger().info("-" * 50)
    
    def init_vosk(self):
        """Inicializa VOSK"""
        model_path = "model-vosk-es-small"
        
        if not os.path.exists(model_path):
            self.get_logger().error(f" Modelo no encontrado en {model_path}")
            self.get_logger().info("Descarga con: wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip")
            return
        
        self.get_logger().info("Cargando VOSK...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.recognizer.SetWords(False)
        self.get_logger().info(" VOSK listo")
    
    def init_audio(self):
        """Inicializa audio"""
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024,
            input_device_index=None,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def detectar_keyword(self, texto):
        """Detecta si el texto empieza con 'robot'"""
        if not texto:
            return False, ""
        
        texto_lower = texto.lower().strip()
        
        if texto_lower.startswith(self.keyword):
            resto = texto_lower[len(self.keyword):].strip()
            return True, resto
        
        palabras = texto_lower.split()
        if len(palabras) > 0 and palabras[0] == self.keyword:
            resto = " ".join(palabras[1:])
            return True, resto
        
        return False, ""
    
    def ejecutar_comando(self, comando):
        """Convierte comando de voz a Twist y publica"""
        comando_lower = comando.lower()
        twist = Twist()
        twist.linear = Vector3(x=0.0, y=0.0, z=0.0)
        twist.angular = Vector3(x=0.0, y=0.0, z=0.0)
        
        # Detectar tipo de comando
        if any(word in comando_lower for word in ['adelante', 'avanza', 'sigue', 've hacia adelante']):
            twist.linear.x = 0.2  # 0.2 m/s
            self.get_logger().info(f" COMANDO: Adelante")
            
        elif any(word in comando_lower for word in ['atrás', 'retrocede', 've hacia atrás']):
            twist.linear.x = -0.2
            self.get_logger().info(f" COMANDO: Atrás")
            
        elif any(word in comando_lower for word in ['izquierda', 'gira izquierda', 've a la izquierda']):
            twist.angular.z = 0.5  # 0.5 rad/s
            self.get_logger().info(f" COMANDO: Gira izquierda")
            
        elif any(word in comando_lower for word in ['derecha', 'gira derecha', 've a la derecha']):
            twist.angular.z = -0.5
            self.get_logger().info(f" COMANDO: Gira derecha")
            
        elif any(word in comando_lower for word in ['detente', 'para', 'stop']):
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.get_logger().info(f" COMANDO: Detener")
            self.cmd_vel_pub.publish(twist)
            return
        
        else:
            self.get_logger().info(f" Comando no reconocido: '{comando}'")
            return
        
        # Publicar comando
        self.cmd_vel_pub.publish(twist)
        self.get_logger().info(f"   Publicado: linear={twist.linear.x}, angular={twist.angular.z}")
        
        # Auto-stop después de 2 segundos
        def stop_after_delay():
            time.sleep(2)
            twist_stop = Twist()
            twist_stop.linear = Vector3(x=0.0, y=0.0, z=0.0)
            twist_stop.angular = Vector3(x=0.0, y=0.0, z=0.0)
            self.cmd_vel_pub.publish(twist_stop)
            self.get_logger().info(" Auto-stop (2s)")
        
        threading.Thread(target=stop_after_delay, daemon=True).start()
    
    def loop_principal(self):
        """Loop de escucha"""
        self.get_logger().info("\n Escuchando... (di 'Robot' + comando)")
        
        while rclpy.ok() and self.is_listening:
            try:
                # Obtener audio
                data = self.audio_queue.get(timeout=1)
                
                # Procesar con VOSK
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    texto = result.get('text', '')
                    
                    if texto:
                        tiene_keyword, resto = self.detectar_keyword(texto)
                        
                        if tiene_keyword:
                            self.get_logger().info(f"\n Detectado: '{texto}'")
                            if resto:
                                self.ejecutar_comando(resto)
                            else:
                                self.get_logger().info("   Robot: ¿Dígame?")
                            
                            self.get_logger().info("\n Escuchando...")
                
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.get_logger().error(f"Error: {e}")
    
    def destroy_node(self):
        """Limpieza"""
        self.is_listening = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        
        # Asegurar motores detenidos
        twist_stop = Twist()
        twist_stop.linear = Vector3(x=0.0, y=0.0, z=0.0)
        twist_stop.angular = Vector3(x=0.0, y=0.0, z=0.0)
        self.cmd_vel_pub.publish(twist_stop)
        
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = VoiceMotorTest()
    
    # Hilo para el loop de ROS
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    
    # Hilo para el loop de voz
    voice_thread = threading.Thread(target=node.loop_principal)
    voice_thread.daemon = True
    voice_thread.start()
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info(" Deteniendo...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
