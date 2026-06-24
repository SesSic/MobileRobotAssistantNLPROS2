#!/usr/bin/env python3
import json
import numpy as np
import os
from sentence_transformers import SentenceTransformer
import pickle

# Rutas
KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/knowledge")
JSON_PATH = os.path.join(KNOWLEDGE_DIR, "responses.json")
EMBEDDINGS_PATH = os.path.join(KNOWLEDGE_DIR, "embeddings.npy")
QUESTIONS_PATH = os.path.join(KNOWLEDGE_DIR, "questions_list.pkl")
METADATA_PATH = os.path.join(KNOWLEDGE_DIR, "metadata.pkl")

print(" Cargando modelo...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print(f" Leyendo {JSON_PATH}")
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extraer preguntas y respuestas
preguntas = [item["pregunta"] for item in data]
respuestas = [item["respuesta"] for item in data]
keywords = [item.get("keywords", []) for item in data]

print(f" {len(preguntas)} preguntas cargadas")
print(" Generando embeddings...")

# Generar embeddings
embeddings = model.encode(preguntas, show_progress_bar=True)

# Guardar
np.save(EMBEDDINGS_PATH, embeddings)
with open(QUESTIONS_PATH, 'wb') as f:
    pickle.dump(preguntas, f)
with open(METADATA_PATH, 'wb') as f:
    pickle.dump({"respuestas": respuestas, "keywords": keywords}, f)

print(f" Embeddings guardados en {EMBEDDINGS_PATH}")
print(f"   Shape: {embeddings.shape}")
