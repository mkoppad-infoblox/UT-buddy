# This script splits 'testing_document.txt' into chunks using '>?<' as a delimiter,
# generates embeddings for each chunk using Ollama's embedding API, and stores them in a JSON file.

import requests
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "llama3:8b"

# Use a popular, efficient model for semantic search
SENTENCE_MODEL = "BAAI/bge-large-en-v1.5"

def split_document_by_delimiter(filepath, delimiter=">?<"):
    with open(filepath, "r") as f:
        content = f.read()
    # Split and keep empty chunks to preserve chunk count
    raw_chunks = content.split(delimiter)
    # Remove leading/trailing whitespace but keep empty chunks
    chunks = [chunk.strip() for chunk in raw_chunks]
    # Remove trailing empty chunks only (from accidental delimiters at end)
    while chunks and not chunks[-1]:
        chunks.pop()
    return chunks

def get_embedding(text):
    model = getattr(get_embedding, 'model', None)
    if model is None:
        model = SentenceTransformer(SENTENCE_MODEL)
        get_embedding.model = model
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist() if hasattr(emb, 'tolist') else emb

def main():
    chunks = split_document_by_delimiter("testing_document.txt", ">?<")
    embeddings = []
    chunk_texts = []
    for i, chunk in enumerate(chunks, 1):
        try:
            embedding = get_embedding(chunk)
            if embedding is not None:
                embeddings.append(embedding)
                chunk_texts.append({"chunk_id": i, "text": chunk})
            print(f"Embedded chunk {i}")
        except Exception as e:
            print(f"Error embedding chunk {i}: {e}")
    if embeddings:
        embeddings_np = np.array(embeddings, dtype=np.float32)
        index = faiss.IndexFlatIP(embeddings_np.shape[1])
        faiss.normalize_L2(embeddings_np)
        index.add(embeddings_np)
        faiss.write_index(index, "chunk.index")
        with open("chunk_texts.json", "w") as f:
            json.dump(chunk_texts, f, indent=2)
        print("FAISS index saved to chunk.index and chunk metadata to chunk_texts.json")
    else:
        print("No embeddings to save.")

if __name__ == "__main__":
    main()
