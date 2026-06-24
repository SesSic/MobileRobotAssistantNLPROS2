#!/usr/bin/env python3
import subprocess
import json
import time

def consultar_phi(prompt, max_tokens=20, temperatura=0.1):
    """
    Consulta a Phi-2 vía Ollama con parámetros controlados
    """
    # Construir el prompt completo con instrucciones
    prompt_completo = prompt
    
    comando = [
        "ollama", "run", "qwen2.5:1.5b-instruct-q4_0",
        prompt_completo
    ]

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=20  # Aumentado a 20 segundos para Phi-2
        )
        return resultado.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Lo siento, la consulta tardó demasiado"
    except Exception as e:
        return f"Error: {e}"

def prompt_matematicas(pregunta):
    prompt = f"""Responde SOLO con el número. No expliques nada.

Pregunta: {pregunta}
Respuesta:"""
    return consultar_phi(prompt, max_tokens=5, temperatura=0.0)

def prompt_lenguaje(pregunta):
    # Forzar que NO repita la palabra original
    prompt = f"""Da SOLO el sinónimo, una palabra diferente.
La palabra NO puede ser la misma que la original.

Ejemplo:
Pregunta: sinónimo de rápido
Respuesta: veloz

Pregunta: {pregunta}
Respuesta:"""
    return consultar_phi(prompt, max_tokens=5, temperatura=0.3)

def prompt_general(pregunta):
    prompt = f"""Responde breve, máximo 2 oraciones.

Pregunta: {pregunta}
Respuesta:"""
    return consultar_phi(prompt, max_tokens=50, temperatura=0.2)

# Prueba
if __name__ == "__main__":
    print(" Probando Phi-2 con prompts específicos\n")
    
    pruebas = [
        ("matematicas", "cuanto es 6 por 4"),
        ("lenguaje", "sinonimo de feliz"),
        ("general", "Cuanto tiempo goberno Rafael Correa Delgado en Ecuador")
    ]
    
    for tipo, pregunta in pruebas:
        print(f"\n Tipo: {tipo}")
        print(f" Pregunta: {pregunta}")
        
        if tipo == "matematicas":
            respuesta = prompt_matematicas(pregunta)
        elif tipo == "lenguaje":
            respuesta = prompt_lenguaje(pregunta)
        else:
            respuesta = prompt_general(pregunta)
            
        print(f" Respuesta: {respuesta}")
        print("-" * 50)
