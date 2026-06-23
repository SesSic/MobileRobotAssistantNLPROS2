#!/usr/bin/env python3
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

# Configuración
BASE_DIR = "/home/sessic/robot_educativo_ws/src/robot_voice/robot_voice"
JSON_PATH = os.path.join(BASE_DIR, "data/knowledge/responses.json")
UMBRAL = 0.65
DIFERENCIA_MINIMA = 0.15

# Cargar modelo y datos
model = SentenceTransformer('all-MiniLM-L6-v2')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Preparar textos enriquecidos
textos_enriquecidos = []
for item in data:
    pregunta = item["pregunta"]
    keywords = " ".join(item.get("keywords", []))
    texto = f"{pregunta} {keywords} {keywords}"
    textos_enriquecidos.append(texto)

embeddings = model.encode(textos_enriquecidos)
respuestas = [item["respuesta"] for item in data]
preguntas = [item["pregunta"] for item in data]

def detectar_tipo_pregunta(texto):
    texto = texto.lower()
    
    # Matemáticas
    if any(p in texto for p in ["cuánto es", "cuanto es", "suma", "resta", 
                                 "multiplica", "divide", "por", "más","mas", "menos", 
                                 "entre", "mitad de", "número sigue","numero sigue","numero le sigue","número le sigue","dividido"]):
        return "matematicas"
    
    # Lenguaje
    if any(p in texto for p in ["sinónimo","sinonimo", "antónimo","antonimo", "plural de", 
                                 "tipo de palabra", "adverbio", "qué significa"]):
        return "lenguaje"
    
    return "general"

def buscar_en_cache(consulta):
    emb_consulta = model.encode([consulta])
    similitudes = cosine_similarity(emb_consulta, embeddings)[0]
    
    indices = np.argsort(similitudes)[-3:][::-1]
    mejor_idx = indices[0]
    mejor_sim = similitudes[mejor_idx]
    segunda_sim = similitudes[indices[1]] if len(indices) > 1 else 0
    
    if mejor_sim >= UMBRAL:
        if (mejor_sim - segunda_sim) >= DIFERENCIA_MINIMA:
            return {
                "accion": "responder",
                "respuesta": respuestas[mejor_idx],
                "confianza": mejor_sim,
                "pregunta": preguntas[mejor_idx]
            }
    
    return {
        "accion": "tinyllama",
        "confianza": mejor_sim,
        "tipo": "general"
    }

# Prueba interactiva
print(" Probador de intenciones (escribe 'salir' para terminar)\n")

while True:
    consulta = input("\n Pregunta: ")
    if consulta.lower() == 'salir':
        break
    
    tipo = detectar_tipo_pregunta(consulta)
    print(f" Tipo detectado: {tipo}")
    
    if tipo != "general":
        print(f" Usaría TinyLlama modo {tipo}")
        # Aquí iría la llamada a TinyLlama con prompt especializado
    else:
        resultado = buscar_en_cache(consulta)
        if resultado["accion"] == "responder":
            print(f" RESPONDO: {resultado['respuesta']}")
            print(f"   (match con: {resultado['pregunta']} - {resultado['confianza']:.4f})")
        else:
            print(f" Baja confianza ({resultado['confianza']:.4f}) - Usaría TinyLlama general")#!/usr/bin/env python3
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

# ConfiguraciÃ³n
BASE_DIR = "/home/sessic/robot_educativo_ws/src/robot_voice/robot_voice"
JSON_PATH = os.path.join(BASE_DIR, "data/knowledge/responses.json")
UMBRAL = 0.65
DIFERENCIA_MINIMA = 0.15

# Cargar modelo y datos
model = SentenceTransformer('all-MiniLM-L6-v2')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Preparar textos enriquecidos
textos_enriquecidos = []
for item in data:
    pregunta = item["pregunta"]
    keywords = " ".join(item.get("keywords", []))
    texto = f"{pregunta} {keywords} {keywords}"
    textos_enriquecidos.append(texto)

embeddings = model.encode(textos_enriquecidos)
respuestas = [item["respuesta"] for item in data]
preguntas = [item["pregunta"] for item in data]

def detectar_tipo_pregunta(texto):
    texto = texto.lower()
    
    # MatemÃ¡ticas
    if any(p in texto for p in ["cuÃ¡nto es", "cuanto es", "suma", "resta", 
                                 "multiplica", "divide", "por", "mÃ¡s", "menos", 
                                 "entre", "mitad de", "nÃºmero sigue"]):
        return "matematicas"
    
    # Lenguaje
    if any(p in texto for p in ["sinÃ³nimo", "antÃ³nimo", "plural de", 
                                 "tipo de palabra", "adverbio", "quÃ© significa"]):
        return "lenguaje"
    
    return "general"

def buscar_en_cache(consulta):
    emb_consulta = model.encode([consulta])
    similitudes = cosine_similarity(emb_consulta, embeddings)[0]
    
    indices = np.argsort(similitudes)[-3:][::-1]
    mejor_idx = indices[0]
    mejor_sim = similitudes[mejor_idx]
    segunda_sim = similitudes[indices[1]] if len(indices) > 1 else 0
    
    if mejor_sim >= UMBRAL:
        if (mejor_sim - segunda_sim) >= DIFERENCIA_MINIMA:
            return {
                "accion": "responder",
                "respuesta": respuestas[mejor_idx],
                "confianza": mejor_sim,
                "pregunta": preguntas[mejor_idx]
            }
    
    return {
        "accion": "tinyllama",
        "confianza": mejor_sim,
        "tipo": "general"
    }

# Prueba interactiva
print(" Probador de intenciones (escribe 'salir' para terminar)\n")

while True:
    consulta = input("\n Pregunta: ")
    if consulta.lower() == 'salir':
        break
    
    tipo = detectar_tipo_pregunta(consulta)
    print(f" Tipo detectado: {tipo}")
    
    if tipo != "general":
        print(f" UsarÃ­a TinyLlama modo {tipo}")
        # AquÃ­ irÃ­a la llamada a TinyLlama con prompt especializado
    else:
        resultado = buscar_en_cache(consulta)
        if resultado["accion"] == "responder":
            print(f" RESPONDO: {resultado['respuesta']}")
            print(f"   (match con: {resultado['pregunta']} - {resultado['confianza']:.4f})")
        else:
            print(f" Baja confianza ({resultado['confianza']:.4f}) - UsarÃ­a TinyLlama general")