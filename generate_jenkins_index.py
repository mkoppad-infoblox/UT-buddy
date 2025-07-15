from sentence_transformers import SentenceTransformer
import faiss
import pickle

# Load Jenkins documentation
with open("jenkins_docs.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

# Split into chunks
def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

jenkins_chunks = split_text(full_text)

# Load embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Generate embeddings
embeddings = model.encode(jenkins_chunks, normalize_embeddings=True)

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

# Save index and metadata
faiss.write_index(index, "jenkins_docs_index.faiss")
with open("jenkins_docs_metadata.pkl", "wb") as f:
    pickle.dump(jenkins_chunks, f)

print("✅ Jenkins FAISS index and metadata saved.")
