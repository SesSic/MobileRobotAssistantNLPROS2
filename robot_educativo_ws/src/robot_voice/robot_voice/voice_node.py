#!/usr/bin/env python3
"""
NODO DE VOZ UNIFICADO PARA ROBOT EDUCATIVO
Versión: Edge TTS (online) + Piper (offline)
Modos: Educación (solo voz) y Navegación (todos los nodos)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import String, Bool
import json
import time
import threading
import queue
import subprocess
import os
import sys
import tempfile
import re
import threading

# VOSK y audio
from vosk import Model, KaldiRecognizer
import pyaudio

# Importar procesador unificado
from .unified_processor import UnifiedProcessor

class VoiceNode(Node):
    def __init__(self):
        super().__init__('voice_node')

        # ============ CONFIGURACIÓN ============
        self.declare_parameters(
            namespace='',
            parameters=[
                ('keyword', 'robot'),
                ('audio.sample_rate', 16000),
                ('audio.channels', 1),
                ('audio.device.mic', 'hw:1,0'),
                ('audio.device.speaker', 'plughw:2,0'),
                ('vosk.model_path', '/home/YOURUSER/robot_educativo_ws/model-vosk-es-small'),
                ('motor.auto_stop_duration', 2.0),
                ('motor.speed_linear', 0.18),
                ('motor.speed_angular', 2.5),
                ('tts.voice_online', 'es-CL-CatalinaNeural'),
                ('tts.voice_offline', 'es_MX-claude-high'),
                ('tts.speed', 150),
                ('piper_path', '/home/YOURUSER/piper/piper'),
                ('startup_message', ''),
                ('speak_only', False),                  
            ]
        )
        
        # Obtener parámetros
        self.keyword = self.get_parameter('keyword').value.lower()
        self.sample_rate = self.get_parameter('audio.sample_rate').value
        self.channels = self.get_parameter('audio.channels').value
        self.mic_device = self.get_parameter('audio.device.mic').value
        self.speaker_device = self.get_parameter('audio.device.speaker').value
        self.vosk_model_path = self.get_parameter('vosk.model_path').value
        self.auto_stop_duration = self.get_parameter('motor.auto_stop_duration').value
        self.motor_speed_linear = self.get_parameter('motor.speed_linear').value
        self.motor_speed_angular = self.get_parameter('motor.speed_angular').value
        self.tts_voice_online = self.get_parameter('tts.voice_online').value
        self.tts_voice_offline = self.get_parameter('tts.voice_offline').value
        self.piper_path = self.get_parameter('piper_path').value
        self.speak_only = self.get_parameter('speak_only').value 
    
    
        self.cola_respuestas = queue.Queue()
        self.hilo_reproduccion = threading.Thread(target=self.reproducir_cola)
        self.hilo_reproduccion.daemon = True
        self.hilo_reproduccion.start()
        # ============ ESTADO ============
        self.is_listening = True
        self.processing = False
        self.audio_queue = queue.Queue()
        
        # Control de motores
        self.active_movement = False
        self.movement_timer = None
        
        # ============ MODO DE OPERACIÓN ============
        self.modo = "educacion"  # "educacion" o "navegacion" (por defecto educación)
        
        # ============ MEMORIA VISUAL ============
        self.ultima_deteccion = None
        self.ultima_descripcion = "No he visto nada aún. Di 'Robot ¿qué ves?' para activar la cámara."
        self.objetos_detectados = []
        
        # ============ PUBLICADORES ============
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.listening_pub = self.create_publisher(Bool, '/voice/is_listening', 10)
        self.command_pub = self.create_publisher(String, '/voice/detected_command', 10)
        self.response_pub = self.create_publisher(String, '/voice/response', 10)
        
        self.follower_stop_pub = self.create_publisher(String, '/vision/follower/stop', 10)
        self.follower_target_pub = self.create_publisher(String, '/vision/follower/target', 10)
        
        # ============ SUSCRIPTORES ============
        self.scene_sub = self.create_subscription(String, '/vision/scene_description', self.scene_callback, 10)
        self.detections_sub = self.create_subscription(String, '/vision/detections', self.detections_callback, 10)
        
        # ============ INICIALIZAR COMPONENTES ============
        if not self.speak_only:
            self.init_vosk()
            self.init_unified_processor()
            self.init_audio()
        
            self.status_timer = self.create_timer(1.0, self.status_callback)
        
            # Iniciar hilo de escucha
            self.listening_thread = threading.Thread(target=self.listening_loop)
            self.listening_thread.daemon = True
            self.listening_thread.start()
        else:
            self.get_logger().info("Modo SOLO HABLAR activado - sin micrófono")

        subprocess.run(['ffmpeg', '-version'], capture_output=True)

        startup_msg = self.get_parameter('startup_message').value
        if startup_msg:
            # Esperar un poco a que todo esté listo
            threading.Timer(2.0, lambda: self.hablar(startup_msg)).start()
                
    # ============ CALLBACKS DE VISIÓN ============
    
    def scene_callback(self, msg):
        self.ultima_descripcion = msg.data
    
    def detections_callback(self, msg):
        try:
            self.ultima_deteccion = json.loads(msg.data)
            self.objetos_detectados = []
            for det in self.ultima_deteccion.get('detections', []):
                obj_class = det.get('class', '')
                if obj_class not in self.objetos_detectados:
                    self.objetos_detectados.append(obj_class)
        except Exception as e:
            self.get_logger().error(f"Error procesando detecciones: {e}")
    
    # ============ MÉTODOS DE VOSK ============
    
    def init_vosk(self):
        if not os.path.exists(self.vosk_model_path):
            self.get_logger().warning(f"Modelo no encontrado en: {self.vosk_model_path}")
        
        try:
            self.vosk_model = Model(self.vosk_model_path)
            self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            self.vosk_recognizer.SetWords(False)
        except Exception as e:
            self.get_logger().error(f"Error cargando VOSK: {e}")
            sys.exit(1)
    
    def init_unified_processor(self):
        try:
            self.processor = UnifiedProcessor(config={
                'timeout_local': 60,
                'check_internet': True
            })
        except Exception as e:
            self.get_logger().error(f"Error cargando procesador: {e}")
            self.processor = None
    
    def init_audio(self):
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024,
                input_device_index=None,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
        except Exception as e:
            self.get_logger().error(f"Error inicializando audio: {e}")
            sys.exit(1)
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def status_callback(self):
        msg = Bool()
        msg.data = self.is_listening and not self.processing
        self.listening_pub.publish(msg)
    
    def check_internet_rapido(self, timeout=2):
        """Verifica conexión a internet rápido"""
        try:
            subprocess.run(['ping', '-c', '1', '-W', str(timeout), '8.8.8.8'], 
                         timeout=timeout, capture_output=True)
            return True
        except:
            return False
    
    def detectar_keyword(self, texto):
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
    
    # ============ CLASIFICACIÓN DE COMANDOS ============
    
    def clasificar_comando(self, texto):
        texto_lower = texto.lower()
        
        # Comandos para cambiar de modo
        if "modo navegacion" in texto_lower or "modo navegación" in texto_lower:
            return 'cambiar_modo', 'navegacion'
        if "modo educacion" in texto_lower or "modo educación" in texto_lower:
            return 'cambiar_modo', 'educacion'
        
        patrones_ver = [
            'qué ves', 'que ves', 'qué hay', 'que hay',
            'qué ves?', 'que ves?', 'qué hay?', 'que hay?',
            'describe', 'describe lo que ves', 'dime qué ves',
            'qué ves ahora', 'qué hay delante', 'qué estás viendo',
            'hay alguien', 'hay personas', 'hay obstáculos',
            'ves algo', 'qué ves en el entorno'
        ]
        
        for patron in patrones_ver:
            if patron in texto_lower or texto_lower == patron.replace('?', ''):
                return 'ver', texto
        
        patrones_ir = [
            've a', 've hacia', 've a la', 've hacia la',
            'sigue', 'sigue a', 'sigue la',
            'acércate a', 'acércate a la',
            'busca', 'encuentra', 'localiza',
            've a la puerta', 've a la silla', 've a la persona',
            'dónde está', 'donde esta'
        ]
        
        for patron in patrones_ir:
            if patron in texto_lower:
                objeto = self.extraer_objeto(texto_lower)
                if objeto:
                    return 'ir', objeto
                else:
                    return 'ir', texto
        
        if any(word in texto_lower for word in ['adelante', 'avanza', 'sigue derecho']):
            return 'movimiento', 'adelante'
        elif any(word in texto_lower for word in ['atrás', 'retrocede', 've atrás']):
            return 'movimiento', 'atras'
        elif any(word in texto_lower for word in ['izquierda', 'gira izquierda']):
            return 'movimiento', 'izquierda'
        elif any(word in texto_lower for word in ['derecha', 'gira derecha']):
            return 'movimiento', 'derecha'
        elif any(word in texto_lower for word in ['detente', 'para', 'stop']):
            return 'movimiento', 'detente'
        elif any(word in texto_lower for word in ['apaga sistema', 'apagar sistema', 'shutdown']):
            return 'sistema', 'apagar'
        
        return 'academico', texto
    
    def extraer_objeto(self, texto):
        objetos_validos = [
            'puerta', 'persona', 'silla', 'mesa', 'mochila',
            'personas', 'sillas', 'mesas', 'mochilas',
            'door', 'chair', 'table', 'backpack', 'person'
        ]
        
        for objeto in objetos_validos:
            if objeto in texto:
                if objeto == 'personas':
                    return 'persona'
                elif objeto == 'sillas':
                    return 'silla'
                elif objeto == 'mesas':
                    return 'mesa'
                elif objeto == 'mochilas':
                    return 'mochila'
                elif objeto == 'door':
                    return 'puerta'
                elif objeto == 'chair':
                    return 'silla'
                elif objeto == 'table':
                    return 'mesa'
                elif objeto == 'backpack':
                    return 'mochila'
                elif objeto == 'person':
                    return 'persona'
                else:
                    return objeto
        
        palabras = texto.split()
        if len(palabras) > 0:
            return palabras[-1]
        
        return None
    
    # ============ CONTROL DE MODOS ============
    
    def controlar_nodos(self, modo):
        """Activa o desactiva nodos según el modo"""
        if modo == "navegacion":
            self.get_logger().info("Activando modo NAVEGACIÓN")
            
            # Lanzar nodos de navegación
            subprocess.Popen(['ros2', 'run', 'robot_navigation', 'motor_controller_node'])
            subprocess.Popen(['ros2', 'run', 'robot_navigation', 'imu_odometry_node'])
            subprocess.Popen(['ros2', 'run', 'robot_navigation', 'ultrasonic_node'])
            subprocess.Popen(['ros2', 'launch', 'robot_vision', 'detection_launch.py','camera_id:=0','confidence:=0.25'])
            subprocess.Popen(['ros2', 'run', 'robot_vision', 'object_follower_node'])
            
        else:  # modo educación
            self.get_logger().info("Activando modo EDUCACIÓN")
            
            # Matar nodos de navegación (dejar solo voz)
            subprocess.run(['pkill', '-f', 'motor_controller_node'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'imu_odometry_node'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'ultrasonic_node'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'detection.launch.py'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'object_follower_node'],stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'usb_camera_node'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'object_detector_node'], stderr=subprocess.DEVNULL)
            
    def cambiar_modo(self, nuevo_modo):
        """Cambia entre modo educación y navegación"""
        if nuevo_modo == self.modo:
            self.hablar(f"Ya estoy en modo {self.modo}")
            return
        
        self.modo = nuevo_modo
        self.controlar_nodos(nuevo_modo)
        
        if nuevo_modo == "navegacion":
            self.hablar("Modo navegación activado. Puedes darme órdenes de movimiento")
        else:
            self.hablar("Modo educación activado. Puedes hacerme preguntas")
        
        self.get_logger().info(f"Modo cambiado a: {nuevo_modo}")
    
    # ============ EJECUCIÓN DE COMANDOS ============
    
    def ejecutar_movimiento(self, comando):
        twist = Twist()
        twist.linear = Vector3(x=0.0, y=0.0, z=0.0)
        twist.angular = Vector3(x=0.0, y=0.0, z=0.0)
        
        if self.movement_timer and self.movement_timer.is_alive():
            self.movement_timer.cancel()
        
        if comando == 'adelante':
            twist.linear.x = self.motor_speed_linear
        elif comando == 'atras':
            twist.linear.x = -self.motor_speed_linear
        elif comando == 'izquierda':
            twist.angular.z = self.motor_speed_angular
        elif comando == 'derecha':
            twist.angular.z = -self.motor_speed_angular
        elif comando == 'detente':
            self.cmd_vel_pub.publish(twist)
            if hasattr(self, 'follower_stop_pub'):
                stop_msg = String()
                stop_msg.data = "stop"
                self.follower_stop_pub.publish(stop_msg)
            return
        else:
            return
        
        self.cmd_vel_pub.publish(twist)
        
        def auto_stop():
            time.sleep(self.auto_stop_duration)
            twist_stop = Twist()
            self.cmd_vel_pub.publish(twist_stop)
        
        self.movement_timer = threading.Timer(self.auto_stop_duration, auto_stop)
        self.movement_timer.daemon = True
        self.movement_timer.start()
    
    def ejecutar_ir(self, objeto):
        if not self.ultima_deteccion:
            self.hablar("Primero tengo que ver el entorno. Di 'Robot ¿qué ves?'")
            return
        
        if objeto not in self.objetos_detectados:
            encontrado = False
            for obj in self.objetos_detectados:
                if objeto in obj or obj in objeto:
                    objeto = obj
                    encontrado = True
                    break
            
            if not encontrado:
                self.hablar(f"No vi ningún {objeto} hace un momento. Di 'Robot ¿qué ves?' para actualizar")
                return
        
        target_msg = String()
        target_msg.data = objeto
        self.follower_target_pub.publish(target_msg)
        self.hablar(f"Buscando {objeto}")
    
    def ejecutar_ver(self):
        if self.ultima_descripcion == "No he visto nada aún. Di 'Robot ¿qué ves?' para activar la cámara.":
            time.sleep(1)
        self.hablar(self.ultima_descripcion)
    
    # ============ TTS: EDGE (ONLINE) Y PIPER (OFFLINE) ============
    
    def hablar(self, texto):
        if not texto:
            return
        
        # Publicar respuesta para otros nodos
        msg = String()
        msg.data = texto
        self.response_pub.publish(msg)
        
        # Intentar Edge TTS primero (online)
        if self.check_internet_rapido():
            self.hablar_edge(texto)
        else:
            # Fallback a Piper (offline)
            self.hablar_piper(texto)
    
    def hablar_edge(self, texto):
        """Edge TTS con pipeline directo - Voz chilena CatalinaNeural"""
        try:
            # Escapar comillas y caracteres especiales para el shell
            texto_escapado = texto.replace('"', '\\"').replace("'", "\\'").replace('`', '\\`').replace('$', '\\$')
            
            # Pipeline directo: edge-tts | ffmpeg | aplay
            edge = subprocess.Popen(
                ['edge-tts', '--text', texto, '--voice', self.tts_voice_online, '--write-media', '-'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            ffmpeg = subprocess.Popen(
                ['ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-ar', '16000', '-ac', '1', '-loglevel', 'error', '-'],
                stdin=edge.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            aplay = subprocess.Popen(
                ['aplay', '-D', self.speaker_device, '-f', 'S16_LE', '-r', '16000'],
                stdin=ffmpeg.stdout,
                stderr=subprocess.PIPE
            )
            
            # Cerrar pipes para evitar deadlocks
            edge.stdout.close()
            ffmpeg.stdout.close()
            
            # Esperar a que termine con timeout
            aplay.wait(timeout=10)
            
        except subprocess.TimeoutExpired:
            self.get_logger().error("Timeout en Edge TTS")
            self.hablar_piper(texto)
        except Exception as e:
            self.get_logger().error(f"Error en Edge TTS: {e}")
            self.hablar_piper(texto)
    
    def reproducir_cola(self):
        """Hilo dedicado a reproducir respuestas una tras otra"""
        while True:
            texto = self.cola_respuestas.get()
            if texto is None:
                break
            # Usar hablar_edge directamente (o hablar_piper)
            self.hablar_edge(texto)
            self.cola_respuestas.task_done()
            
    def hablar(self, texto):
        """Encola el texto para reproducir en orden"""
        self.cola_respuestas.put(texto)
    
    def verificar_audio(self):
        """Verifica si el audio responde"""
        try:
            subprocess.run(
                ['aplay', '-D', self.speaker_device, '--dump-hw-params'],
                timeout=1,
                capture_output=True,
                check=True
            )
            return True
        except:
            return False
        
    def hablar_piper(self, texto):
        """Piper TTS offline - Voz mexicana claude-high"""
        try:
            cmd = f'echo "{texto}" | {self.piper_path} --model {self.tts_voice_offline} --output-raw | aplay -r 22050 -f S16_LE -t raw -D {self.speaker_device}'
            subprocess.run(cmd, shell=True, timeout=15)
        except Exception as e:
            self.get_logger().error(f"Error en Piper TTS: {e}")
    
    def procesar_comando(self, tipo, comando, texto_original):
        """Procesa el comando usando el procesador unificado"""
        cmd_msg = String()
        cmd_msg.data = texto_original
        self.command_pub.publish(cmd_msg)
        
        # Manejar cambio de modo
        if tipo == 'cambiar_modo':
            self.cambiar_modo(comando)
            return
        
        # ============ FILTRAR COMANDOS SEGÚN MODO ============
        if self.modo == "educacion":
            if tipo == 'movimiento' or tipo == 'ir':
                self.hablar("Estoy en modo educación. Activa modo navegacion para activar movimiento")
                return
        elif self.modo == "navegacion":
            if tipo == 'academico':
                self.hablar("Estoy en modo navegación. Activa modo educacion para hacer preguntas")
                return
        # =====================================================
        
        
        
        # ============ FEEDBACK INMEDIATO ============
        if tipo in ['academico', 'ver']:
            self.procesando_comando = True
            
            def decir_ok():
                time.sleep(0.3)  # Pequeña pausa para asegurar orden
                if self.procesando_comando:  # Si aún no responde
                    self.cola_respuestas.put("Ok")
            
            threading.Thread(target=decir_ok).start()
        # ============================================
        
        if tipo == 'movimiento':
            self.ejecutar_movimiento(comando)
            
        elif tipo == 'ver':
            self.ejecutar_ver()
            
        elif tipo == 'ir':
            self.ejecutar_ir(comando)
            
        elif tipo == 'sistema':
            if comando == 'apagar':
                self.ejecutar_apagar_sistema()
            
        else:  # academico
            if self.processor:
                try:
                    resultado = self.processor.procesar_pregunta(comando)
                    respuesta = resultado['respuesta']

                    self.procesando_comando = False
                    self.cola_respuestas.put(respuesta)
               
                except Exception as e:
                    self.get_logger().error(f"Error en procesador: {e}")
                    self.cola_respuestas.put("Lo siento, tuve un problema procesando la pregunta")
            else:
                self.cola_respuestas.put("El procesador de lenguaje no está disponible")
    
    # NUEVA FUNCIÓN
    def ejecutar_apagar_sistema(self):
        """Apaga el sistema de forma segura"""
        self.get_logger().warn("⚠️ COMANDO DE APAGADO RECIBIDO")
        
        # Mensaje de voz
        threading.Thread(target=self.hablar, args=("Apagando sistema",)).start()
        
        # Esperar 5 segundos para que termine de hablar
        time.sleep(5)
        
        try:
            # Ejecutar sudo shutdown (con contraseña)
            subprocess.run(f'echo sebastian072 | sudo -S shutdown now', 
                         shell=True, timeout=2)
        except Exception as e:
            self.get_logger().error(f"Error en apagado: {e}")
    
    # ============ LOOP PRINCIPAL DE ESCUCHA ============
    
    def listening_loop(self):
        time.sleep(2)
        buffer_parcial = ""
        
        while rclpy.ok() and self.is_listening:
            try:
                data = self.audio_queue.get(timeout=1)
                
                if self.vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self.vosk_recognizer.Result())
                    texto = result.get('text', '')
                    
                    if texto:
                        tiene_keyword, resto = self.detectar_keyword(texto)
                        
                        if tiene_keyword:
                            if resto:
                                tipo, comando = self.clasificar_comando(resto)
                                self.procesar_comando(tipo, comando, resto)
                            else:
                                self.hablar("¿Dígame?")
                
                else:
                    partial = json.loads(self.vosk_recognizer.PartialResult())
                    texto_parcial = partial.get('partial', '')
                    
                    if texto_parcial and texto_parcial != buffer_parcial:
                        buffer_parcial = texto_parcial
                
            except queue.Empty:
                continue
            except Exception as e:
                self.get_logger().error(f"Error en loop: {e}")
                time.sleep(0.5)
    
    def destroy_node(self):
        self.is_listening = False
        
        twist_stop = Twist()
        self.cmd_vel_pub.publish(twist_stop)
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VoiceNode()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()