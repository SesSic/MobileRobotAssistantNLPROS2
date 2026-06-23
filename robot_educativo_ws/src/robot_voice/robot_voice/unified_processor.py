#!/usr/bin/env python3
"""
Unified Processor for Robot Educational Assistant
Integra: Cache semántico, clasificador de intenciones, Qwen local y Trinity online
"""

import json
import numpy as np
import os
import time
import subprocess
import requests
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any, Optional, Tuple

class UnifiedProcessor:
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa todos los componentes del sistema unificado
        
        Args:
            config: Diccionario de configuración (rutas, umbrales, etc.)
        """
        # Configuración por defecto
        self.config = {
            # Rutas base
            'base_dir': "/home/YOURUSER/robot_educativo_ws/src/robot_voice/robot_voice",
            'json_path': "data/knowledge/responses.json",
            
            # Umbrales del cache semántico
            'umbral_cache': 0.65,
            'diferencia_minima': 0.15,
            
            # Configuración modelos
            'modelo_embedding': 'all-MiniLM-L6-v2',
            'modelo_local': 'qwen2.5:1.5b-instruct-q4_0',
            
            # Configuración Trinity
            'openrouter_api_key': "Insert API Key",
            'trinity_model': "arcee-ai/trinity-large-preview:free",
            
            # Timeouts
            'timeout_local': 90,
            'timeout_trinity': 20,
            
            # Control de internet (se detecta automáticamente)
            'check_internet': True
        }
        
        # Actualizar con configuración proporcionada
        if config:
            self.config.update(config)
        
        # Construir rutas completas
        self.json_path = os.path.join(
            self.config['base_dir'], 
            self.config['json_path']
        )
        
        # Inicializar componentes
        # PRINT ELIMINADO: Inicializando UnifiedProcessor...
        self._init_embedding_model()
        self._init_cache_data()
        self._init_intent_patterns()
        # PRINT ELIMINADO: UnifiedProcessor listo!

    def _precargar_modelo_local(self):
        """Precarga el modelo Qwen en memoria"""
        # PRINT ELIMINADO: Precargando modelo local Qwen...
        try:
            # Consulta dummy para cargar el modelo
            subprocess.run(
                ["ollama", "run", self.config['modelo_local'], "Hola"],
                capture_output=True,
                timeout=30
            )
            # PRINT ELIMINADO: Modelo local precargado
        except Exception as e:
            print(f"No se pudo precargar: {e}")  # MANTENER error

    def _init_embedding_model(self):
        """Carga el modelo de embeddings"""
        # PRINT ELIMINADO: Cargando modelo de embeddings...
        self.model = SentenceTransformer(self.config['modelo_embedding'])
    
    def _init_cache_data(self):
        """Carga los datos del cache semántico"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Preparar textos enriquecidos con keywords
            self.textos_enriquecidos = []
            for item in data:
                pregunta = item["pregunta"]
                keywords = " ".join(item.get("keywords", []))
                texto = f"{pregunta} {keywords} {keywords}"
                self.textos_enriquecidos.append(texto)
            
            # Generar embeddings si no existen, sino cargarlos
            embeddings_path = os.path.join(
                self.config['base_dir'], 
                "data/knowledge/embeddings.npy"
            )
            metadata_path = os.path.join(
                self.config['base_dir'], 
                "data/knowledge/metadata.pkl"
            )
            questions_path = os.path.join(
                self.config['base_dir'], 
                "data/knowledge/questions_list.pkl"
            )
            
            if os.path.exists(embeddings_path) and os.path.exists(metadata_path):
                # PRINT ELIMINADO: Cargando embeddings pre-generados...
                self.embeddings = np.load(embeddings_path)
                import pickle
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                self.respuestas = metadata['respuestas']
                
                with open(questions_path, 'rb') as f:
                    self.preguntas = pickle.load(f)
                
                # PRINT ELIMINADO: Cache cargado con X entradas
                # PRINT ELIMINADO: Embeddings shape
            
            else:
                # PRINT ELIMINADO: Generando embeddings nuevos...
                self.embeddings = self.model.encode(self.textos_enriquecidos)
                self.respuestas = [item["respuesta"] for item in data]
                self.preguntas = [item["pregunta"] for item in data]
                
                os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)
                np.save(embeddings_path, self.embeddings)
                import pickle
                with open(metadata_path, 'wb') as f:
                    pickle.dump({
                        'respuestas': self.respuestas,
                        'preguntas': self.preguntas
                    }, f)
            
            # PRINT ELIMINADO: Cache cargado con X entradas
            
        except Exception as e:
            print(f" Error cargando cache: {e}")  # MANTENER error
            self.embeddings = np.array([])
            self.respuestas = []
            self.preguntas = []
            self.textos_enriquecidos = []
    
    def _init_intent_patterns(self):
        """Define los patrones para clasificación de intenciones"""
        self.intent_patterns = {
            'matematicas': [
                "cuánto es", "cuanto es", "suma", "resta", 
                "multiplica", "divide", "por", "más", "mas", "menos", 
                "entre", "mitad de", "número sigue", "numero sigue",
                "número le sigue", "número que sigue", "doble de",
                "triple de", "mitad de", "calcula", "resultado de",
                "cuánto da", "cuanto da"
            ],
            'lenguaje': [
                "sinónimo", "sinonimo", "antónimo", "antonimo", 
                "plural de", "singular de", 
                "adverbio", "verbo de", "sustantivo de","predicado de","sujeto de", "adjetivo de","masculino de","femenino de"
            ]
        }
        
        self.intent_patterns_lower = {
            intent: [p.lower() for p in patterns]
            for intent, patterns in self.intent_patterns.items()
        }
    
    def check_internet(self, timeout=3) -> bool:
        """Verifica si hay conexión a internet"""
        if not self.config['check_internet']:
            return True
        
        try:
            requests.get("https://www.google.com", timeout=timeout)
            return True
        except:
            try:
                requests.get("https://www.cloudflare.com", timeout=timeout)
                return True
            except:
                return False
   
    def detectar_intencion(self, texto: str) -> str:
        """
        Detecta si la pregunta es de matemáticas, lenguaje o general
        """
        texto_lower = texto.lower()
        
        tiene_numeros = bool(re.search(r'\d+', texto_lower))
        operadores_condicionales = ['por', 'más', 'mas', 'menos', 'entre','mitad de']
        
        for pattern in self.intent_patterns_lower['matematicas']:
            if pattern in texto_lower:
                if pattern in operadores_condicionales and not tiene_numeros:
                    continue
                return "matematicas"
        
        for pattern in self.intent_patterns_lower['lenguaje']:
            if pattern in texto_lower:
                return "lenguaje"
        
        return "general"
   
    def buscar_en_cache(self, consulta: str) -> Dict[str, Any]:
        """Busca la consulta en el cache semántico"""
        if len(self.embeddings) == 0:
            return {
                "accion": "generar",
                "confianza": 0.0,
                "tipo": "general"
            }
        
        emb_consulta = self.model.encode([consulta])
        similitudes = cosine_similarity(emb_consulta, self.embeddings)[0]
        
        indices = np.argsort(similitudes)[-3:][::-1]
        mejor_idx = indices[0]
        mejor_sim = similitudes[mejor_idx]
        segunda_sim = similitudes[indices[1]] if len(indices) > 1 else 0
        
        if mejor_sim >= self.config['umbral_cache']:
            if (mejor_sim - segunda_sim) >= self.config['diferencia_minima']:
                return {
                    "accion": "responder",
                    "respuesta": self.respuestas[mejor_idx],
                    "confianza": mejor_sim,
                    "pregunta": self.preguntas[mejor_idx],
                    "fuente": "cache"
                }
        
        return {
            "accion": "generar",
            "confianza": mejor_sim,
            "tipo": "general"
        }
    
    def consultar_qwen_local(self, prompt: str, modo: str = "general") -> str:
        """Consulta el modelo local Qwen 2.5 1.5B"""
        if modo == "matematicas":
            prompt_completo = f"""Responde SOLO con el número. No expliques nada. No agregues texto adicional.

Pregunta: {prompt}
Respuesta:"""
            max_tokens = 5
            temperatura = 0.0
            
        elif modo == "lenguaje":
            prompt_lower = prompt.lower()
            es_palabra_unica = any(p in prompt_lower for p in [
                "sinónimo de", "sinonimo de", "antónimo de", "antonimo de",
                "plural de", "singular de", "masculino de", "femenino de"
            ])
            es_analisis_oracion = any(p in prompt_lower for p in [
                "verbo de", "sustantivo de", "adjetivo de", 
                "predicado de", "sujeto de", "adverbio de"
            ])
            
            if es_palabra_unica:
                prompt_completo = f"""Da SOLO la palabra solicitada. Una sola palabra, la respuesta correcta.
No expliques, no des ejemplos, solo la palabra.

Pregunta: {prompt}
Respuesta:"""
                max_tokens = 10
                temperatura = 0.3
                
            elif es_analisis_oracion:
                if "de la oracion" in prompt_lower:
                    partes = prompt.lower().split("de la oracion")
                    pregunta_tipo = partes[0].strip()
                    oracion = partes[1].strip()
                else:
                    palabras = prompt.split()
                    pregunta_tipo = " ".join(palabras[:4])
                    oracion = " ".join(palabras[4:])
                
                prompt_completo = f"""Analiza la siguiente oración y responde SOLO lo que se pide, máximo 2 palabras.

Oración: "{oracion}"
Pregunta: {pregunta_tipo}
Respuesta:"""
                max_tokens = 20
                temperatura = 0.2
            
        else:  # general
            prompt_completo = f"""Responde de forma breve y concisa, máximo 2 oraciones completas.
Ve directo al punto, sin introducciones ni explicaciones extras.

Pregunta: {prompt}
Respuesta:"""
            max_tokens = 50
            temperatura = 0.2

        comando = ["ollama", "run", self.config['modelo_local'], prompt_completo]
        
        try:
            inicio = time.time()
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=self.config['timeout_local']
            )
            tiempo = time.time() - inicio
            
            respuesta = resultado.stdout.strip()
            
            if modo == "matematicas":
                numeros = re.findall(r'-?\d+\.?\d*', respuesta)
                if numeros:
                    respuesta = numeros[0]
            
            elif modo == "lenguaje":
                primera_palabra = respuesta.split()[0] if respuesta.split() else respuesta
                respuesta = primera_palabra
            
            # PRINT ELIMINADO: Qwen local (modo) - Xs
            return respuesta
            
        except subprocess.TimeoutExpired:
            return "Lo siento, la consulta tardó demasiado"
        except Exception as e:
            return f"Error en modelo local: {str(e)}"
    
    def consultar_trinity(self, pregunta: str) -> Tuple[str, float]:
        """Consulta Trinity vía OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.config['openrouter_api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config['trinity_model'],
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un asistente directo y conciso. Responde en máximo 2 oraciones completas. Ve al grano."
                },
                {
                    "role": "user",
                    "content": pregunta
                }
            ],
            "max_tokens": 200,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            inicio = time.time()
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config['timeout_trinity']
            )
            fin = time.time()
            tiempo = fin - inicio
            
            if r.status_code == 200:
                respuesta = r.json()["choices"][0]["message"]["content"]
                respuesta_corta = self._acortar_respuesta(respuesta)
                # PRINT ELIMINADO: Trinity online - Xs
                return respuesta_corta, tiempo
            else:
                return f"Error Trinity: {r.status_code}", 0
                
        except requests.exceptions.Timeout:
            return "Error: Timeout en Trinity", 0
        except Exception as e:
            return f"Error en Trinity: {str(e)}", 0
    
    def _acortar_respuesta(self, texto: str, max_oraciones: int = 2) -> str:
        """Toma solo las primeras N oraciones completas"""
        oraciones = re.split(r'\.\s+', texto)
        
        if len(oraciones) <= max_oraciones:
            return texto
        
        return '. '.join(oraciones[:max_oraciones]) + '.'
    
    def procesar_pregunta(self, pregunta: str) -> Dict[str, Any]:
        """
        Método principal que procesa una pregunta
        """
        inicio_total = time.time()
        # PRINT ELIMINADO: Procesando: '{pregunta}'
        
        intencion = self.detectar_intencion(pregunta)
        # PRINT ELIMINADO: Intención detectada: {intencion}
        
        cache_result = self.buscar_en_cache(pregunta)

        if cache_result['accion'] == 'responder':
            tiempo_total = time.time() - inicio_total
            return {
                'pregunta': pregunta,
                'respuesta': cache_result['respuesta'],
                'intencion': intencion,
                'fuente': 'cache',
                'tiempo': tiempo_total,
                'confianza': cache_result['confianza'],
                'pregunta_match': cache_result['pregunta']
            }

        tiene_internet = self.check_internet()

        # PRINT ELIMINADO: Internet: ✅/❌
        
        if tiene_internet:
            respuesta, _ = self.consultar_trinity(pregunta)
            fuente = 'trinity_online'
        else:
            respuesta = self.consultar_qwen_local(pregunta, modo=intencion)
            fuente = f'qwen_local_{intencion}'
        
        tiempo_total = time.time() - inicio_total
        return {
            'pregunta': pregunta,
            'respuesta': respuesta,
            'intencion': intencion,
            'fuente': fuente,
            'tiempo': tiempo_total,
            'confianza': cache_result.get('confianza', 0.0)
        }

# ===== MODO DE PRUEBA INTERACTIVA =====
def main():
    """Modo interactivo para probar el procesador unificado"""
    print("=" * 60)
    print(" UNIFIED PROCESSOR - MODO PRUEBA")
    print("=" * 60)
    
    processor = UnifiedProcessor()
    
    print("\n Comandos especiales:")
    print("  'salir' - Terminar programa")
    print("  'test'  - Ejecutar batería de pruebas")
    print("  'stats' - Ver estadísticas")
    print("-" * 60)
    
    historial = []
    
    while True:
        pregunta = input("\n  Pregunta: ").strip()
        
        if pregunta.lower() == 'salir':
            break
        
        elif pregunta.lower() == 'test':
            print("\n EJECUTANDO BATERÍA DE PRUEBAS")
            pruebas = [
                ("matematicas", "¿Cuánto es 8 por 7?"),
                ("matematicas", "¿Cuánto es 15 + 23?"),
                ("lenguaje", "Dame un sinónimo de rápido"),
                ("lenguaje", "¿Qué significa 'efímero'?"),
                ("general", "¿Quién fue Albert Einstein?"),
                ("general", "¿Cuál es la capital de Francia?"),
                ("general", "¿Qué es la fotosíntesis?")
            ]
            
            for tipo, test_pregunta in pruebas:
                print(f"\n--- [{tipo}] ---")
                resultado = processor.procesar_pregunta(test_pregunta)
                print(f"RESPUESTA: {resultado['respuesta']}")
                print(f"Fuente: {resultado['fuente']} | Tiempo: {resultado['tiempo']:.2f}s")
                historial.append(resultado)
            
            continue
        
        elif pregunta.lower() == 'stats':
            print("\n ESTADÍSTICAS")
            if not historial:
                print("   No hay consultas aún")
                continue
            
            fuentes = {}
            for r in historial:
                fuente = r['fuente']
                fuentes[fuente] = fuentes.get(fuente, 0) + 1
            
            print(f"   Total consultas: {len(historial)}")
            print("   Distribución:")
            for fuente, count in fuentes.items():
                print(f"     - {fuente}: {count}")
            continue
        
        if not pregunta:
            continue
        
        resultado = processor.procesar_pregunta(pregunta)
        historial.append(resultado)
        
        print(f"\n RESPUESTA: {resultado['respuesta']}")
        print(f"    [{resultado['fuente']}] - {resultado['tiempo']:.2f}s")
        if resultado['intencion'] != 'general':
            print(f"    Intención: {resultado['intencion']}")
        if resultado['fuente'] == 'cache':
            print(f"    Match: {resultado['pregunta_match']} ({resultado['confianza']:.2f})")

if __name__ == "__main__":
    main()