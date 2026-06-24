from sentence_transformers import SentenceTransformer
import numpy as np

# 1. Cargar modelo (all-MiniLM-L6-v2 es pequeño: 384 dimensiones)
print("Cargando modelo...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Modelo cargado")

# 2. Tus preguntas de prueba
preguntas = [
    "¿Qué es la fotosíntesis?",
    "¿Cómo hacen las plantas su comida?",
    "¿Qué es un robot?",
    "¿Dime sobre máquinas autónomas?"
]

# 3. Generar embeddings
print("Generando embeddings...")
embeddings = model.encode(preguntas)
print(f"Shape: {embeddings.shape}")  # (4, 384)

# 4. Ver similitud entre preguntas
from sklearn.metrics.pairwise import cosine_similarity

similitud = cosine_similarity(embeddings)
print("\nMatriz de similitud:")
print(similitud)

# 5. Probar una búsqueda simple
consulta = "¿Cómo convierten las plantas la luz en energía?"
embedding_consulta = model.encode([consulta])

similitudes = cosine_similarity(embedding_consulta, embeddings)[0]
indice_mejor = np.argmax(similitudes)
print(f"\nConsulta: {consulta}")
print(f"Mejor match: {preguntas[indice_mejor]}")
print(f"Similitud: {similitudes[indice_mejor]:.4f}")
