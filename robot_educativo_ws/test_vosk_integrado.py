#!/usr/bin/env python3
"""
Script de prueba para VOSK con palabra clave "Robot"
Integrado con:
- arecord para grabar
- espeak para hablar
- UnifiedProcessor para respuestas
- Palabra clave "Robot" para activación
"""

import pyaudio
import json
import time
import queue
import sys
import os
import subprocess
import tempfile
import threading
import numpy as np
from vosk import Model, KaldiRecognizer

# Importar tu procesador unificado
from unified_processor import UnifiedProcessor

class VoskTestNode:
    def __init__(self, keyword="robot"):
        """
        Inicializa el nodo de prueba con VOSK
        """
        self.keyword = keyword.lower()
        self.is_listening = True
        self.processing = False
        self.audio_queue = queue.Queue()
        
        # Configuración de audio (igual que en tu nodo)
        self.sample_rate = 16000
        self.channels = 1
        self.duration = 3  # segundos de grabación
        self.mic_device = "hw:1,0"      # Tu micrófono
        self.speaker_device = "plughw:2,0"  # Tu parlante
        
        print("=" * 60)
        print(" PRUEBA VOSK + PROCESADOR UNIFICADO")
        print("=" * 60)
        
        # Inicializar VOSK
        self.init_vosk()
        
        # Inicializar procesador unificado
        print("\n Cargando procesador de lenguaje...")
        start = time.time()
        self.processor = UnifiedProcessor(config={
           'timeout_local': 50  # Reducir timeout de 20s a 10s
       })
        end = time.time()
        print(f"   Procesador cargado en {end-start:.2f}s")
        
        # Configurar audio
        self.init_audio()
        
        print("\n Listo! Di 'Robot' seguido de tu pregunta")
        print("   Ejemplo: 'Robot ¿cuánto es 2 más 2?'")
        print("   Ejemplo: 'Robot sinónimo de rápido'")
        print("   Ejemplo: 'Robot ¿qué es la fotosíntesis?'")
        print("-" * 60)
    
    def init_vosk(self):
        """Inicializa VOSK con modelo en español"""
        model_path = "model-vosk-es-small"
        
        print(f"\n Buscando modelo VOSK en: {model_path}")
        
        # Si no existe, intentar descargar
        if not os.path.exists(model_path):
            print("    Modelo no encontrado. Intentando descargar...")
            try:
                subprocess.run([
                    "wget", "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
                ], check=True)
                subprocess.run(["unzip", "vosk-model-small-es-0.42.zip"], check=True)
                subprocess.run(["mv", "vosk-model-small-es-0.42", model_path], check=True)
                subprocess.run(["rm", "vosk-model-small-es-0.42.zip"], check=True)
                print("    Modelo descargado")
            except Exception as e:
                print(f"    Error descargando: {e}")
                print("   Descárgalo manualmente de: https://alphacephei.com/vosk/models")
                sys.exit(1)
        
        # Cargar modelo
        print("   Cargando modelo VOSK...")
        start = time.time()
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.recognizer.SetWords(False)
        end = time.time()
        print(f"    VOSK cargado en {end-start:.2f}s")
    
    def init_audio(self):
        """Inicializa PyAudio"""
        self.audio = pyaudio.PyAudio()
        
        # Listar dispositivos (debug)
        print("\n Dispositivos de audio:")
        for i in range(self.audio.get_device_count()):
            dev = self.audio.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                print(f"   Entrada {i}: {dev['name']}")
        
        # Abrir stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024,
            input_device_index=None,  # Usar default
            stream_callback=self.audio_callback
        )
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback del stream de audio"""
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def detectar_keyword(self, texto):
        """
        Detecta si el texto comienza con "robot"
        Retorna: (tiene_keyword, resto_del_texto)
        """
        if not texto:
            return False, ""
        
        texto_lower = texto.lower().strip()
        
        # Caso 1: Empieza exactamente con "robot"
        if texto_lower.startswith(self.keyword):
            resto = texto_lower[len(self.keyword):].strip()
            return True, resto
        
        # Caso 2: La primera palabra es "robot"
        palabras = texto_lower.split()
        if len(palabras) > 0 and palabras[0] == self.keyword:
            resto = " ".join(palabras[1:])
            return True, resto
        
        return False, ""
    
    def grabar_audio(self, duracion=None):
        """
        Graba audio usando arecord (igual que tu nodo)
        """
        if duracion is None:
            duracion = self.duration
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmpfile:
            audio_file = tmpfile.name
        
        try:
            cmd = [
                'arecord', '-D', self.mic_device,
                '-f', 'S16_LE',
                '-r', str(self.sample_rate),
                '-c', str(self.channels),
                '-d', str(duracion),
                '-q', audio_file
            ]
            
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                          timeout=duracion + 2)
            
            if os.path.getsize(audio_file) < 1000:
                os.unlink(audio_file)
                return None
            return audio_file
            
        except Exception as e:
            print(f"Error grabando: {e}")
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            return None
    
    def hablar(self, texto):
        """
        Texto a voz con espeak (igual que tu nodo)
        """
        if not texto:
            return
        
        print(f"\n ROBOT DICE: {texto}")
        
        try:
            # Usar espeak-ng (o espeak si no tienes el -ng)
            espeak_cmd = ['espeak-ng', '-v', 'es', '-s', '150', '--stdout', texto]
            
            # Verificar si espeak-ng existe
            try:
                subprocess.run(['which', 'espeak-ng'], check=True, capture_output=True)
            except:
                espeak_cmd = ['espeak', '-v', 'es', '-s', '150', '--stdout', texto]
            
            espeak = subprocess.Popen(
                espeak_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            aplay = subprocess.Popen(
                ['aplay', '-D', self.speaker_device, '-q'],
                stdin=espeak.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            espeak.wait()
            aplay.wait()
            
        except Exception as e:
            print(f"Error TTS: {e}")
    
    def loop_principal(self):
        """
        Loop principal: escucha continuamente con VOSK
        """
        print("\n Escuchando... (di 'Robot' para activar)")
        
        buffer_parcial = ""
        
        while self.is_listening:
            try:
                # Obtener audio de la cola
                data = self.audio_queue.get(timeout=1)
                
                # Procesar con VOSK
                if self.recognizer.AcceptWaveform(data):
                    # Resultado final
                    result = json.loads(self.recognizer.Result())
                    texto = result.get('text', '')
                    
                    if texto:
                        tiene_keyword, resto = self.detectar_keyword(texto)
                        
                        if tiene_keyword:
                            print(f"\n Detectado: '{texto}'")
                            
                            if resto:
                                print(f"   Procesando: '{resto}'")
                                
                                # ¡AQUÍ USAMOS TU PROCESADOR!
                                resultado = self.processor.procesar_pregunta(resto)
                                
                                print(f"   Respuesta: {resultado['respuesta']}")
                                print(f"   Fuente: {resultado['fuente']} | Tiempo: {resultado['tiempo']:.2f}s")
                                
                                # Hablar respuesta
                                self.hablar(resultado['respuesta'])
                            else:
                                print("   Robot: ¿Dígame?")
                                self.hablar("¿Dígame?")
                            
                            print("\n Escuchando...")
                        else:
                            # Solo mostrar si no es muy común
                            if len(texto) > 3:
                                print(f"   Ignorado: '{texto}' (sin palabra clave)")
                
                else:
                    # Resultado parcial (mientras habla)
                    partial = json.loads(self.recognizer.PartialResult())
                    texto_parcial = partial.get('partial', '')
                    
                    # Mostrar solo si cambia
                    if texto_parcial and texto_parcial != buffer_parcial:
                        # No mostrar si es muy corto
                        if len(texto_parcial) > 3:
                            print(f"    {texto_parcial}", end='\r')
                        buffer_parcial = texto_parcial
                
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error en loop: {e}")
    
    def start(self):
        """Inicia el nodo"""
        self.stream.start_stream()
        
        try:
            self.loop_principal()
        except KeyboardInterrupt:
            print("\n\nDeteniendo...")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el nodo"""
        self.is_listening = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        print(" Detenido")

def main():
    detector = VoskTestNode()
    detector.start()

if __name__ == "__main__":
    main()
