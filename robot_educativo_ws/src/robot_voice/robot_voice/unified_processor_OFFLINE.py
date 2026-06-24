#!/usr/bin/env python3
"""
Unified Processor - VERSION SOLO QWEN LOCAL
Sin cache semantico, solo modelo local
"""

import time
import subprocess
import re
from typing import Dict, Any, Optional

class UnifiedProcessor:
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el procesador - VERSION SOLO LOCAL SIN CACHE
        """
        # Configuracion por defecto
        self.config = {
            'modelo_local': 'qwen2.5:1.5b-instruct-q4_0',
            'timeout_local': 60,
        }
        
        # Actualizar con configuracion proporcionada
        if config:
            self.config.update(config)
    
    def _acortar_respuesta(self, texto: str, max_oraciones: int = 2) -> str:
        """Toma solo las primeras N oraciones completas"""
        if not texto:
            return texto
        oraciones = re.split(r'\.\s+', texto)
        if len(oraciones) <= max_oraciones:
            return texto
        return '. '.join(oraciones[:max_oraciones]) + '.'
    
    def consultar_qwen_local(self, pregunta: str) -> str:
        """
        Consulta el modelo local Qwen 2.5 1.5B
        """
        prompt_completo = f"""Responde de forma breve y concisa, maximo 2 oraciones completas.
Ve directo al punto, sin introducciones ni explicaciones extras.

Pregunta: {pregunta}
Respuesta:"""

        comando = [
            "ollama", "run", self.config['modelo_local'],
            prompt_completo
        ]
        
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=self.config['timeout_local']
            )
            
            respuesta = resultado.stdout.strip()
            return self._acortar_respuesta(respuesta)
            
        except subprocess.TimeoutExpired:
            return "Lo siento, la consulta tardo demasiado"
        except Exception as e:
            return f"Error en modelo local: {str(e)}"
    
    def procesar_pregunta(self, pregunta: str) -> Dict[str, Any]:
        """
        Metodo principal - solo usa Qwen local
        """
        inicio_total = time.time()
        
        respuesta = self.consultar_qwen_local(pregunta)
        tiempo_total = time.time() - inicio_total
        
        return {
            'pregunta': pregunta,
            'respuesta': respuesta,
            'fuente': 'qwen_local',
            'tiempo': tiempo_total
        }


# ===== MODO DE PRUEBA INTERACTIVA =====
def main():
    """Modo interactivo para probar el procesador local"""
    print("=" * 60)
    print(" UNIFIED PROCESSOR - MODO SOLO LOCAL")
    print("=" * 60)
    
    processor = UnifiedProcessor()
    
    print("\n Comandos especiales:")
    print("  'salir' - Terminar programa")
    print("-" * 60)
    
    while True:
        pregunta = input("\n Pregunta: ").strip()
        
        if pregunta.lower() == 'salir':
            break
        
        if not pregunta:
            continue
        
        resultado = processor.procesar_pregunta(pregunta)
        
        print(f"\n RESPUESTA: {resultado['respuesta']}")
        print(f"    [{resultado['fuente']}] - {resultado['tiempo']:.2f}s")

if __name__ == "__main__":
    main()
