#!/usr/bin/env python3
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os
import unicodedata
import re

# Configuracion
BASE_DIR = "/home/sessic/robot_educativo_ws/src/robot_voice/robot_voice"
JSON_PATH = os.path.join(BASE_DIR, "data/knowledge/responses.json")
UMBRAL = 0.70
PESO_PREGUNTA = 0.7
PESO_KEYWORDS = 0.3

# Stopwords para filtrar palabras irrelevantes
STOPWORDS = {'el', 'la', 'los', 'las', 'de', 'del', 'a', 'ante', 'bajo', 'con', 
             'contra', 'desde', 'durante', 'en', 'entre', 'hacia', 'hasta', 
             'mediante', 'para', 'por', 'segun', 'sin', 'sobre', 'tras', 'un', 
             'una', 'unos', 'unas', 'que', 'cual', 'cuales', 'como', 'cuando', 
             'donde', 'quien', 'quienes', 'es', 'son', 'fue', 'eran', 'ser', 
             'tiene', 'tienen', 'hay', 'esta', 'estan', 'estar', 'con', 'sin',
             'mas', 'pero', 'porque', 'ya', 'tan', 'tanto', 'cada', 'ante', 'bajo'}

# Cargar modelo y datos
model = SentenceTransformer('all-MiniLM-L6-v2')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Preguntas y keywords por separado
preguntas = [item["pregunta"] for item in data]
respuestas = [item["respuesta"] for item in data]
keywords_list = [" ".join(item.get("keywords", [])) for item in data]

# Embeddings por separado
preguntas_emb = model.encode(preguntas)
keywords_emb = model.encode(keywords_list)

def normalizar_texto(texto):
    """Elimina acentos, signos y convierte a minusculas"""
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto

def obtener_tipo_pregunta(texto):
    """Extrae el tipo de pregunta (que, quien, cuando, donde, como, cuanto)"""
    texto_lower = texto.lower()
    
    tipos = {
        'que': ['que', 'qué'],
        'quien': ['quien', 'quién'],
        'cuando': ['cuando', 'cuándo'],
        'donde': ['donde', 'dónde'],
        'como': ['como', 'cómo'],
        'cuanto': ['cuanto', 'cuánto', 'cuantos', 'cuántos']
    }
    
    for tipo, palabras in tipos.items():
        if any(p in texto_lower for p in palabras):
            return tipo
    
    return None

def detectar_tipo_pregunta(texto):
    texto = texto.lower()
    
    if any(p in texto for p in ["cuanto es", "suma", "resta", "multiplica", "divide", "por", "mas", "menos", "entre", "mitad de"]):
        return "matematicas"
    
    if any(p in texto for p in ["sinonimo", "antonimo", "plural de", "adverbio", "que significa"]):
        return "lenguaje"
    
    return "general"

def verificar_coherencia(consulta, pregunta_match):
    """Verifica que las palabras clave y tipo de pregunta coincidan"""
    
    consulta_norm = normalizar_texto(consulta)
    pregunta_norm = normalizar_texto(pregunta_match)
    
    tipo_consulta = obtener_tipo_pregunta(consulta)
    tipo_pregunta = obtener_tipo_pregunta(pregunta_match)
    
    print(f"    Debug - Tipo consulta: {tipo_consulta}")
    print(f"    Debug - Tipo pregunta: {tipo_pregunta}")
    
    if tipo_consulta and tipo_pregunta and tipo_consulta != tipo_pregunta:
        print(f"    Rechazado: tipo de pregunta diferente")
        return False
    
    palabras_consulta = set(consulta_norm.split())
    palabras_pregunta = set(pregunta_norm.split())
    
    palabras_consulta_filt = {p for p in palabras_consulta if p not in STOPWORDS and len(p) > 2}
    palabras_pregunta_filt = {p for p in palabras_pregunta if p not in STOPWORDS and len(p) > 2}
    
    palabras_extra = palabras_consulta_filt - palabras_pregunta_filt
    palabras_faltantes = palabras_pregunta_filt - palabras_consulta_filt
    palabras_comunes = palabras_consulta_filt & palabras_pregunta_filt
    
    print(f"    Debug - Comunes: {palabras_comunes}")
    print(f"    Debug - Extra: {palabras_extra}")
    print(f"    Debug - Faltan: {palabras_faltantes}")
    
    if len(palabras_extra) >= 1 and len(palabras_faltantes) >= 1:
        if len(palabras_comunes) > 0:
            total = len(palabras_consulta_filt | palabras_pregunta_filt)
            proporcion = len(palabras_comunes) / total if total > 0 else 0
            print(f"    Debug - Proporcion: {proporcion:.2f}")
            if proporcion >= 0.4:
                return True
            else:
                print(f"    Rechazado: baja proporcion")
                return False
        else:
            print(f"    Rechazado: sin comunes")
            return False
    
    return True

def buscar_en_cache(consulta):
    emb_consulta = model.encode([consulta])
    
    sim_preguntas = cosine_similarity(emb_consulta, preguntas_emb)[0]
    sim_keywords = cosine_similarity(emb_consulta, keywords_emb)[0]
    
    sim_total = PESO_PREGUNTA * sim_preguntas + PESO_KEYWORDS * sim_keywords
    
    indices = np.argsort(sim_total)[-5:][::-1]
    mejor_idx = indices[0]
    mejor_sim = sim_total[mejor_idx]
    
    print(f"\n Busqueda para: '{consulta}'")
    print(f" Mejor candidato: '{preguntas[mejor_idx][:70]}...'")
    print(f" Similitud total: {mejor_sim:.4f} (umbral: {UMBRAL})")
    
    for i, idx in enumerate(indices[:3]):
        print(f"   {i+1}. {preguntas[idx][:50]}... -> total:{sim_total[idx]:.4f} (preg:{sim_preguntas[idx]:.4f}, key:{sim_keywords[idx]:.4f})")
    
    if mejor_sim >= UMBRAL:
        print("   - UMBRAL CUMPLIDO, llamando a verificar_coherencia...")
        if verificar_coherencia(consulta, preguntas[mejor_idx]):
            print(f" VERIFICACION: Aceptado")
            return {
                "accion": "responder",
                "respuesta": respuestas[mejor_idx],
                "confianza": mejor_sim,
                "pregunta": preguntas[mejor_idx]
            }
        else:
            print(f" VERIFICACION: Rechazado")
    
    return {"accion": "tinyllama", "confianza": mejor_sim}

# Prueba interactiva
print(" Probador con KEYWORDS RESTAURADOS")
print(" Peso preguntas: 70%, Peso keywords: 30%\n")

while True:
    consulta = input("\n Pregunta: ")
    if consulta.lower() == 'salir':
        break
    
    tipo = detectar_tipo_pregunta(consulta)
    print(f" Tipo detectado: {tipo}")
    
    if tipo != "general":
        print(f" Usaria TinyLlama modo {tipo}")
    else:
        resultado = buscar_en_cache(consulta)
        if resultado["accion"] == "responder":
            print(f" RESPONDO: {resultado['respuesta']}")
            print(f"   (match con: {resultado['pregunta']} - {resultado['confianza']:.4f})")
        else:
            print(f" Baja confianza ({resultado['confianza']:.4f}) - Usaria TinyLlama general")
