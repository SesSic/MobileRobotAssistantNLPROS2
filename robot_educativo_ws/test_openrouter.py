import requests
import time
import re

API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def consultar_trinity(pregunta):
    data = {
        "model": "arcee-ai/trinity-large-preview:free",
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
    
    inicio = time.time()
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=15
    )
    fin = time.time()
    
    if r.status_code == 200:
        respuesta = r.json()["choices"][0]["message"]["content"]
        return respuesta, fin - inicio
    else:
        return f"Error: {r.status_code}", 0

def acortar_respuesta(texto, max_oraciones=2):
    """Toma solo las primeras N oraciones completas"""
    # Dividir por puntos seguidos de espacio
    oraciones = re.split(r'\.\s+', texto)
    
    if len(oraciones) <= max_oraciones:
        return texto
    
    # Tomar las primeras N oraciones y agregar punto final
    return '. '.join(oraciones[:max_oraciones]) + '.'

# Pruebas
preguntas = [
    "¿Quien es Daniel Noboa Ecuador?",
    "¿Cuál es la capital de Azerbayan?",
    "Dime un sinónimo de clarividente",
    "¿Qué es la melanina?"
]

print(" Probando Trinity Large Preview (modo directo)\n")
print("=" * 60)

for pregunta in preguntas:
    print(f" Pregunta: {pregunta}")
    
    respuesta_completa, tiempo = consultar_trinity(pregunta)
    respuesta_corta = acortar_respuesta(respuesta_completa)
    
    print(f" Tiempo: {tiempo:.2f}s")
    print(f" Completa: {respuesta_completa[:100]}...")
    print(f" Directa: {respuesta_corta}")
    print("-" * 40)
    time.sleep(1)
