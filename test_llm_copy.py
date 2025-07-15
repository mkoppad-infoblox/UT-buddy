
import requests
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3:8b"
SYSTEM_PROMPT = (
    "You are a UT failure assistant. You help users debug and fix errors in their code and unit tests in Python. "
    "If the user's question is related to the provided context, use it to answer. Don't mention the context in the response. "
    "If the question is not related to the context, answer as a general helpful LLM assistant, ignoring the context."
)
SENTENCE_MODEL = "BAAI/bge-large-en-v1.5"


def get_embedding(text):
    model = getattr(get_embedding, 'model', None)
    if model is None:
        model = SentenceTransformer(SENTENCE_MODEL)
        get_embedding.model = model
    emb = model.encode(text, normalize_embeddings=True)
    return emb if isinstance(emb, np.ndarray) else np.array(emb, dtype=np.float32)



def get_most_relevant_chunk(user_input, faiss_index_path="chunk.index", chunk_texts_path="chunk_texts.json", threshold=0.5, top_k=3):
    try:
        index = faiss.read_index(faiss_index_path)
        with open(chunk_texts_path, "r") as f:
            chunk_texts = json.load(f)

        user_emb = get_embedding("Question: " + user_input).reshape(1, -1)
        faiss.normalize_L2(user_emb)

        D, I = index.search(user_emb, top_k)
        # Find the chunk with the highest similarity (score) in top_k
        best_idx = int(I[0][0])
        best_score = float(D[0][0])
        if best_score >= threshold:
            return chunk_texts[best_idx]["text"]
        else:
            return None
    except Exception:
        return None  # fallback to general response


from openai import AzureOpenAI

# Azure OpenAI configuration (replace with your actual values)
api_key = os.getenv("AZURE_API_KEY")
endpoint = "https://hackfest25.openai.azure.com/"
api_version = "2025-01-01-preview"
deployment_name = "gpt-4o"

client = AzureOpenAI(api_key=api_key,
                    azure_endpoint=endpoint,
                    api_version=api_version)

def query_azure_gpt(prompt, reference_text=None, message_history=None):
    messages = []
    if message_history:
        messages.extend(message_history)
    else:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    if reference_text:
        user_content = f"Context:\n{reference_text}\n\nUser question: {prompt}"
    else:
        user_content = prompt
    messages.append({"role": "user", "content": user_content})
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages
        )
        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        return f"Error communicating with Azure OpenAI: {e}"

def main():
    print("Azure GPT-4o Chat. Type 'exit' to quit.")
    last_relevant_chunk = None
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == "exit":
            print("Conversation ended.")
            break
        # Find the most relevant chunk
        relevant_chunk = get_most_relevant_chunk(user_input)
        # If user asks a follow-up (e.g., 'best practices for previous issue'), use last relevant chunk
        if (relevant_chunk is None and last_relevant_chunk is not None and (
            "previous issue" in user_input.lower() or "above issue" in user_input.lower() or "that issue" in user_input.lower()
        )):
            relevant_chunk = last_relevant_chunk
        if relevant_chunk is not None:
            reply = query_azure_gpt(user_input, reference_text=relevant_chunk, message_history=message_history)
            last_relevant_chunk = relevant_chunk
        else:
            reply = query_azure_gpt(user_input, reference_text=None, message_history=message_history)
        print(f"Assistant: {reply}")
        message_history.append({"role": "user", "content": user_input})
        message_history.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    main()
