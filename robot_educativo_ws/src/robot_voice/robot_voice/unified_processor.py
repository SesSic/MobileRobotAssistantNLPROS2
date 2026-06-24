#!/usr/bin/env python3
"""
Unified Processor for Robot Educational Assistant
Integra: Cache semántico con ponderacion pregunta(70%) + keywords(30%),
clasificador de intenciones, Qwen local y Trinity online
"""

import json
import numpy as np
import os
import time
import subprocess
import requests
import re
import unicodedata
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any, Optional, Tuple

class UnifiedProcessor:
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa todos los componentes del sistema unificado
        
        Args:
            config: Diccionario de configuracion (rutas, umbrales, etc.)
        """
        # Configuracion por defecto
        self.config = {
            # Rutas base
            'base_dir': "/home/sessic/robot_educativo_ws/src/robot_voice/robot_voice",
            'json_path': "data/knowledge/responses.json",
            
            # Umbrales del cache semantico
            'umbral_cache': 0.70,
            'peso_pregunta': 0.7,
            'peso_keywords': 0.3,
            
            # Configuracion modelos
            'modelo_embedding': 'all-MiniLM-L6-v2',
            'modelo_local': 'qwen2.5:1.5b-instruct-q4_0',
            
            # Configuracion Trinity
            'openrouter_api_key': "YOUR_OPENROUTER_API_KEY_HERE",
            'trinity_model': "arcee-ai/trinity-large-preview:free",
            
            # Timeouts
            'timeout_local': 60,
            'timeout_trinity': 15,
            
            # Control de internet
            'check_internet': True,
            
            # Stopwords para filtrado
            'stopwords': {'el', 'la', 'los', 'las', 'de', 'del', 'a', 'ante', 'bajo', 'con', 
                         'contra', 'desde', 'durante', 'en', 'entre', 'hacia', 'hasta', 
                         'mediante', 'para', 'por', 'segun', 'sin', 'sobre', 'tras', 'un', 
                         'una', 'unos', 'unas', 'que', 'cual', 'cuales', 'como', 'cuando', 
                         'donde', 'quien', 'quienes', 'es', 'son', 'fue', 'eran', 'ser', 
                         'tiene', 'tienen', 'hay', 'esta', 'estan', 'estar', 'con', 'sin',
                         'mas', 'pero', 'porque', 'ya', 'tan', 'tanto', 'cada', 'ante', 'bajo'}
        }
        
        # Actualizar con configuracion proporcionada
        if config:
            self.config.update(config)
        
        # Construir rutas completas
        self.json_path = os.path.join(
            self.config['base_dir'], 
            self.config['json_path']
        )
        
        # Inicializar componentes
        self._init_embedding_model()
        self._init_cache_data()
        self._init_intent_patterns()

    def _init_embedding_model(self):
        """Carga el modelo de embeddings"""
        print("   Cargando modelo de embeddings...")
        self.model = SentenceTransformer(self.config['modelo_embedding'])
    
    def _init_cache_data(self):
        """Carga los datos del cache semantico con preguntas y keywords por separado"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Guardar preguntas y respuestas
            self.preguntas = [item["pregunta"] for item in data]
            self.respuestas = [item["respuesta"] for item in data]
            
            # Preparar textos de keywords (una sola vez, sin repeticiones)
            self.keywords_texts = []
            for item in data:
                keywords = item.get("keywords", [])
                keywords_text = " ".join(keywords)
                self.keywords_texts.append(keywords_text)
            
            # Generar embeddings por separado
            print(f"   Generando embeddings para {len(self.preguntas)} preguntas...")
            self.preguntas_emb = self.model.encode(self.preguntas)
            
            print(f"   Generando embeddings para keywords...")
            self.keywords_emb = self.model.encode(self.keywords_texts)
            
            print(f"   Cache cargado con {len(self.respuestas)} entradas")
            print(f"   Embeddings preguntas: {self.preguntas_emb.shape}")
            print(f"   Embeddings keywords: {self.keywords_emb.shape}")
            
        except Exception as e:
            print(f"   Error cargando cache: {e}")
            # Inicializar vacio
            self.preguntas_emb = np.array([])
            self.keywords_emb = np.array([])
            self.respuestas = []
            self.preguntas = []
            self.keywords_texts = []
    
    def _init_intent_patterns(self):
        """Define los patrones para clasificacion de intenciones"""
        self.intent_patterns = {
            'matematicas': [
                "cuanto es", "cuanto es", "suma", "resta", 
                "multiplica", "divide", "por", "mas", "menos", 
                "entre", "mitad de", "numero sigue", "numero sigue",
                "numero le sigue", "numero que sigue", "doble de",
                "triple de", "mitad de", "calcula", "resultado de",
                "cuanto da", "cuanto da", "dividido"
            ],
            'lenguaje': [
                "sinonimo", "sinonimo", "antonimo", "antonimo", 
                "plural de", "singular de", 
                "adverbio", "verbo de", "sustantivo de", "predicado de",
                "sujeto de", "adjetivo de", "masculino de", "femenino de",
                "que significa", "que significa"
            ]
        }
        
        # Compilar para busqueda rapida
        self.intent_patterns_lower = {
            intent: [p.lower() for p in patterns]
            for intent, patterns in self.intent_patterns.items()
        }
    
    def normalizar_texto(self, texto):
        """Elimina acentos, signos y convierte a minusculas"""
        texto = texto.lower()
        texto = re.sub(r'[^\w\s]', '', texto)
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
        return texto
    
    def obtener_tipo_pregunta(self, texto):
        """Extrae el tipo de pregunta (que, quien, cuando, donde, como, cuanto)"""
        texto_lower = texto.lower()
        
        tipos = {
            'que': ['que', 'que'],
            'quien': ['quien', 'quien'],
            'cuando': ['cuando', 'cuando'],
            'donde': ['donde', 'donde'],
            'como': ['como', 'como'],
            'cuanto': ['cuanto', 'cuanto', 'cuantos', 'cuantos']
        }
        
        for tipo, palabras in tipos.items():
            if any(p in texto_lower for p in palabras):
                return tipo
        
        return None
    
    def check_internet(self, timeout=3) -> bool:
        """Verifica si hay conexion a internet"""
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
        Detecta si la pregunta es de matematicas, lenguaje o general
        """
        texto_lower = texto.lower()
        
        # Detectar si hay numeros en el texto
        tiene_numeros = bool(re.search(r'\d+', texto_lower))
        
        # Operadores que necesitan numeros para ser matematicas
        operadores_condicionales = ['por', 'mas', 'menos', 'entre', 'mitad de']
        
        # Matematicas
        for pattern in self.intent_patterns_lower['matematicas']:
            if pattern in texto_lower:
                # Si es un operador condicional, verificar que haya numeros
                if pattern in operadores_condicionales and not tiene_numeros:
                    continue
                return "matematicas"
        
        # Lenguaje
        for pattern in self.intent_patterns_lower['lenguaje']:
            if pattern in texto_lower:
                return "lenguaje"
        
        return "general"
    
    def verificar_coherencia(self, consulta, pregunta_match):
        """Verifica que las palabras clave y tipo de pregunta coincidan"""
        
        consulta_norm = self.normalizar_texto(consulta)
        pregunta_norm = self.normalizar_texto(pregunta_match)
        
        tipo_consulta = self.obtener_tipo_pregunta(consulta)
        tipo_pregunta = self.obtener_tipo_pregunta(pregunta_match)
        
        # Si los tipos de pregunta son diferentes, rechazar inmediatamente
        if tipo_consulta and tipo_pregunta and tipo_consulta != tipo_pregunta:
            return False
        
        # Tokenizar
        palabras_consulta = set(consulta_norm.split())
        palabras_pregunta = set(pregunta_norm.split())
        
        # Filtrar stopwords
        stopwords = self.config['stopwords']
        palabras_consulta_filt = {p for p in palabras_consulta if p not in stopwords and len(p) > 2}
        palabras_pregunta_filt = {p for p in palabras_pregunta if p not in stopwords and len(p) > 2}
        
        # Encontrar diferencias
        palabras_extra = palabras_consulta_filt - palabras_pregunta_filt
        palabras_faltantes = palabras_pregunta_filt - palabras_consulta_filt
        palabras_comunes = palabras_consulta_filt & palabras_pregunta_filt
        
        # Si hay palabras clave diferentes en ambos lados, verificar proporcion de coincidencia
        if len(palabras_extra) >= 1 and len(palabras_faltantes) >= 1:
            if len(palabras_comunes) > 0:
                total_palabras = len(palabras_consulta_filt | palabras_pregunta_filt)
                proporcion_coincidencia = len(palabras_comunes) / total_palabras if total_palabras > 0 else 0
                
                # Aceptar si al menos el 40% de las palabras clave coinciden
                if proporcion_coincidencia >= 0.4:
                    return True
                else:
                    return False
            else:
                return False
        
        # Si no hay diferencias significativas, aceptar
        return True
   
    def buscar_en_cache(self, consulta: str) -> Dict[str, Any]:
        """
        Busca la consulta en el cache semantico usando ponderacion pregunta + keywords
        
        Returns:
            Diccionario con accion y resultados
        """
        if len(self.preguntas_emb) == 0:
            return {
                "accion": "generar",
                "confianza": 0.0,
                "tipo": "general"
            }
        
        # Embedding de la consulta
        emb_consulta = self.model.encode([consulta])
        
        # Calcular similitudes por separado
        sim_preguntas = cosine_similarity(emb_consulta, self.preguntas_emb)[0]
        sim_keywords = cosine_similarity(emb_consulta, self.keywords_emb)[0]
        
        # Combinacion ponderada
        peso_preg = self.config['peso_pregunta']
        peso_key = self.config['peso_keywords']
        sim_total = peso_preg * sim_preguntas + peso_key * sim_keywords
        
        # Obtener top 3
        indices = np.argsort(sim_total)[-3:][::-1]
        mejor_idx = indices[0]
        mejor_sim = sim_total[mejor_idx]
        
        # Verificar si cumple umbral
        if mejor_sim >= self.config['umbral_cache']:
            # Verificacion de coherencia
            if self.verificar_coherencia(consulta, self.preguntas[mejor_idx]):
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
        """
        Consulta el modelo local Qwen 2.5 1.5B
        
        Args:
            prompt: La pregunta del usuario
            modo: "matematicas", "lenguaje", o "general"
        """
        # Construir prompt segun el modo
        if modo == "matematicas":
            prompt_completo = f"""Responde SOLO con el numero. No expliques nada. No agregues texto adicional.

Pregunta: {prompt}
Respuesta:"""
            
        elif modo == "lenguaje":
            # Detectar si es pregunta de palabra unica o necesita explicacion
            prompt_lower = prompt.lower()
            es_palabra_unica = any(p in prompt_lower for p in [
                "sinonimo de", "antonimo de",
                "plural de", "singular de", "masculino de", "femenino de"
            ])
            es_analisis_oracion = any(p in prompt_lower for p in [
                "verbo de", "sustantivo de", "adjetivo de", 
                "predicado de", "sujeto de", "adverbio de"
            ])
            
            if es_palabra_unica:
                prompt_completo = f"""Da SOLO la palabra solicitada. Una sola palabra, la respuesta correcta.
No expliques, no des ejemplos, solo la palabra.

Ejemplos:
Pregunta: sinónimo de rapido
Respuesta: veloz

Pregunta: antónimo de bueno
Respuesta: malo

Pregunta: plural de feliz
Respuesta: felices

Pregunta: singular de casas
Respuesta: casa

Pregunta: masculino de vaca
Respuesta: toro

Pregunta: femenino de caballo
Respuesta: yegua

Pregunta: {prompt}
Respuesta:"""
                
            elif es_analisis_oracion:
                if "de la oracion" in prompt_lower:
                    partes = prompt.lower().split("de la oracion")
                    pregunta_tipo = partes[0].strip()
                    oracion = partes[1].strip()
                else:
                    palabras = prompt.split()
                    pregunta_tipo = " ".join(palabras[:4])
                    oracion = " ".join(palabras[4:])
                
                prompt_completo = f"""Analiza la siguiente oracion y responde SOLO lo que se pide, maximo 2 palabras.

Oracion: "{oracion}"
Pregunta: {pregunta_tipo}

Ejemplos:
Pregunta: cual es el verbo | Oracion: el nino come manzana
Respuesta: come

Pregunta: cual es el adjetivo | Oracion: la casa es grande
Respuesta: grande

Pregunta: cual es el sustantivo | Oracion: Maria corre rapido
Respuesta: Maria

Pregunta: cual es el adverbio | Oracion: corre muy rapido
Respuesta: muy

Pregunta: cual es el sujeto | Oracion: Juan juega futbol
Respuesta: Juan

Pregunta: cual es el predicado | Oracion: Pedro canta bien
Respuesta: canta bien

Ahora responde:
Respuesta:"""
            
            else:
                prompt_completo = f"""Responde de forma breve y concisa, maximo 2 oraciones completas.
Ve directo al punto, sin introducciones ni explicaciones extras.

Pregunta: {prompt}
Respuesta:"""
            
        else:  # general
            prompt_completo = f"""Responde de forma breve y concisa, maximo 2 oraciones completas.
Ve directo al punto, sin introducciones ni explicaciones extras.

Pregunta: {prompt}
Respuesta:"""

        # Ejecutar comando
        comando = [
            "ollama", "run", self.config['modelo_local'],
            prompt_completo
        ]
        
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
            
            # Post-procesamiento segun modo
            if modo == "matematicas":
                # Intentar extraer solo el numero
                numeros = re.findall(r'-?\d+\.?\d*', respuesta)
                if numeros:
                    respuesta = numeros[0]
            
            elif modo == "lenguaje" and es_palabra_unica:
                # Tomar solo la primera palabra
                primera_palabra = respuesta.split()[0] if respuesta.split() else respuesta
                respuesta = primera_palabra
            
            return respuesta
            
        except subprocess.TimeoutExpired:
            return "Lo siento, la consulta tardo demasiado"
        except Exception as e:
            return f"Error en modelo local: {str(e)}"
    
    def consultar_trinity(self, pregunta: str) -> Tuple[str, float]:
        """
        Consulta Trinity via OpenRouter
        
        Returns:
            Tupla (respuesta, tiempo)
        """
        headers = {
            "Authorization": f"Bearer {self.config['openrouter_api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config['trinity_model'],
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un asistente directo y conciso. Responde en maximo 2 oraciones completas. Ve al grano."
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
        Metodo principal que procesa una pregunta siguiendo el flujo definido
        
        Args:
            pregunta: Texto de la pregunta del usuario
            
        Returns:
            Diccionario con respuesta y metadatos
        """
        inicio_total = time.time()
        
        # PASO 1: Clasificar intencion
        intencion = self.detectar_intencion(pregunta)
        
        # PASO 2: Si es matematicas o lenguaje, usar Qwen local directamente
        if intencion in ['matematicas', 'lenguaje']:
            respuesta = self.consultar_qwen_local(pregunta, modo=intencion)
            tiempo_total = time.time() - inicio_total
            return {
                'pregunta': pregunta,
                'respuesta': respuesta,
                'intencion': intencion,
                'fuente': f'qwen_local_{intencion}',
                'tiempo': tiempo_total,
                'confianza': 1.0
            }
        
        # PASO 3: Para general, buscar en cache semantico
        cache_result = self.buscar_en_cache(pregunta)
        
        if cache_result['accion'] == 'responder':
            tiempo_total = time.time() - inicio_total
            return {
                'pregunta': pregunta,
                'respuesta': cache_result['respuesta'],
                'intencion': 'general',
                'fuente': 'cache',
                'tiempo': tiempo_total,
                'confianza': cache_result['confianza'],
                'pregunta_match': cache_result['pregunta']
            }
        
        # PASO 4: Si no hay cache, verificar internet
        tiene_internet = self.check_internet()
        
        if tiene_internet:
            # Usar Trinity online
            respuesta, _ = self.consultar_trinity(pregunta)
            fuente = 'trinity_online'
        else:
            # Fallback a Qwen local general
            respuesta = self.consultar_qwen_local(pregunta, modo='general')
            fuente = 'qwen_local_fallback'
        
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
    
    # Inicializar procesador
    processor = UnifiedProcessor()
    
    print("\n Comandos especiales:")
    print("  'salir' - Terminar programa")
    print("  'test'  - Ejecutar bateria de pruebas")
    print("  'stats' - Ver estadisticas")
    print("-" * 60)
    
    historial = []
    
    while True:
        pregunta = input("\n  Pregunta: ").strip()
        
        if pregunta.lower() == 'salir':
            break
        
        elif pregunta.lower() == 'test':
            print("\n EJECUTANDO BATERIA DE PRUEBAS")
            pruebas = [
                ("matematicas", "Cuanto es 8 por 7"),
                ("matematicas", "Cuanto es 15 + 23"),
                ("lenguaje", "Dame un sinonimo de rapido"),
                ("lenguaje", "Que significa efimero"),
                ("general", "Quien fue Albert Einstein"),
                ("general", "Cual es la capital de Francia"),
                ("general", "Que es la fotosintesis")
            ]
            
            for tipo, test_pregunta in pruebas:
                print(f"\n--- [{tipo}] ---")
                resultado = processor.procesar_pregunta(test_pregunta)
                print(f"RESPUESTA: {resultado['respuesta']}")
                print(f"Fuente: {resultado['fuente']} | Tiempo: {resultado['tiempo']:.2f}s")
                historial.append(resultado)
            
            continue
        
        elif pregunta.lower() == 'stats':
            print("\n ESTADISTICAS")
            if not historial:
                print("   No hay consultas aun")
                continue
            
            fuentes = {}
            for r in historial:
                fuente = r['fuente']
                fuentes[fuente] = fuentes.get(fuente, 0) + 1
            
            print(f"   Total consultas: {len(historial)}")
            print("   Distribucion:")
            for fuente, count in fuentes.items():
                print(f"     - {fuente}: {count}")
            continue
        
        if not pregunta:
            continue
        
        # Procesar pregunta normal
        resultado = processor.procesar_pregunta(pregunta)
        historial.append(resultado)
        
        print(f"\n RESPUESTA: {resultado['respuesta']}")
        print(f"    [{resultado['fuente']}] - {resultado['tiempo']:.2f}s")
        if resultado['intencion'] != 'general':
            print(f"    Intencion: {resultado['intencion']}")
        if resultado['fuente'] == 'cache':
            print(f"    Match: {resultado['pregunta_match']} ({resultado['confianza']:.2f})")

if __name__ == "__main__":
    main()
