import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle

# Load JIRA ticket data
with open("jira_issues_latest.json", "r") as f:
    data = json.load(f)

# Concatenate title and description
corpus = [f"{item['Title']}\n{item['Description']}" for item in data]

# Load BGE-small model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Embed corpus
embeddings = model.encode(corpus, normalize_embeddings=True)

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # IP because embeddings are normalized
index.add(np.array(embeddings))

# Save index and metadata
faiss.write_index(index, "jira_index_latest.faiss")
with open("jira_metadata_latest.pkl", "wb") as f:
    pickle.dump(data, f)

print("✅ Latest FAISS index and metadata saved.")

