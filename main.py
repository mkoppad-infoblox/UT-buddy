from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import json
import requests
import os
import logging
from openai import AzureOpenAI

# Keyword lists for intent detection
greeting_keywords = [
    "hi", "hello", "hey", "yo", "howdy", "greetings", "good morning", "good afternoon", "good evening",
    "what's up", "how are you", "how’s it going", "sup", "hiya", "hey there", "morning", "evening",
    "nice to meet you", "pleased to meet you", "hope you're well", "hope you’re doing well", "how do you do",
    "how have you been", "how are things", "how’s everything", "how’s life", "how’s your day", "how’s your morning",
    "how’s your evening", "how’s your week", "how’s your weekend", "how’s your night", "how’s your afternoon",
    "how’s your day going", "how’s it going today", "how’s it going so far", "how’s it going lately",
    "how’s it going with you", "how’s it going buddy", "how’s it going friend", "how’s it going mate",
    "how’s it going pal", "how’s it going team", "how’s it going assistant", "how’s it going copilot",
    "how’s it going bot", "how’s it going helper", "how’s it going support", "how’s it going engineer",
    "how’s it going dev", "how’s it going developer", "how’s it going tester", "how’s it going qa",
    "how’s it going admin", "how’s it going sysadmin", "how’s it going ops", "how’s it going devops",
    "how’s it going ci", "how’s it going cd", "how’s it going ci/cd", "how’s it going pipeline",
    "how’s it going build", "how’s it going deploy", "how’s it going release", "how’s it going job",
    "how’s it going task", "how’s it going project", "how’s it going sprint", "how’s it going backlog",
    "how’s it going ticket", "how’s it going issue", "how’s it going bug", "how’s it going feature",
    "how’s it going story", "how’s it going epic", "how’s it going test", "how’s it going case",
    "how’s it going suite", "how’s it going plan", "how’s it going run", "how’s it going result",
    "how’s it going report", "how’s it going dashboard", "how’s it going view", "how’s it going config",
    "how’s it going setting", "how’s it going preference", "how’s it going option", "how’s it going menu",
    "how’s it going tab", "how’s it going section", "how’s it going panel", "how’s it going window",
    "how’s it going screen", "how’s it going page", "how’s it going dialog", "how’s it going popup"
]

jenkins_keywords = [
    "jenkins", "pipeline", "job", "build", "freestyle", "agent", "node", "executor", "trigger", "scm",
    "poll scm", "cron", "build step", "post-build", "upstream", "downstream", "view", "log", "console output",
    "workspace", "label", "master", "controller", "slave", "agent pool", "build history", "build trigger",
    "parameter", "environment variable", "artifact", "stage", "step", "scripted pipeline", "declarative pipeline",
    "jenkinsfile", "blue ocean", "dashboard", "configure", "install plugin", "plugin manager", "credentials",
    "webhook", "multibranch", "build status", "build queue", "build executor", "test result", "test report",
    "build failure", "build success", "build duration", "build number", "build cause", "build parameters",
    "pipeline syntax", "pipeline script", "pipeline stage", "pipeline step", "pipeline input", "pipeline output",
    "pipeline environment", "pipeline agent", "pipeline tools", "pipeline options", "pipeline triggers",
    "pipeline post", "pipeline when", "pipeline stages", "pipeline steps", "pipeline parallel", "pipeline matrix",
    "pipeline timeout", "pipeline retry", "pipeline catchError", "pipeline timestamps", "pipeline ansiColor",
    "pipeline checkout", "pipeline sh", "pipeline bat", "pipeline echo", "pipeline readFile", "pipeline writeFile",
    "pipeline archiveArtifacts", "pipeline junit", "pipeline stash", "pipeline unstash"
]


app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Load JIRA index and metadata
index = faiss.read_index("jira_index_latest.faiss")
with open("jira_metadata_latest.pkl", "rb") as f:
    metadata = pickle.load(f)

# Load combined commit data
with open("combined_data.json", "r") as f:
    combined_data = json.load(f)

# Load Jenkins documentation index and metadata
jenkins_index = faiss.read_index("jenkins_docs_index.faiss")
with open("jenkins_docs_metadata.pkl", "rb") as f:
    jenkins_chunks = pickle.load(f)

# Build prompt with context
def build_prompt_with_context(user_message, context_chunks):
    context_text = "\n\n".join(context_chunks)
    system_prompt = (
        "You are a Jenkins assistant. Your job is to help users with Jenkins-related tasks, "
        "such as creating jobs, configuring pipelines, setting up build triggers, and troubleshooting Jenkins errors.\n\n"
        "Use the following Jenkins documentation to help answer the user's question:\n\n"
        f"{context_text}\n\n"
        "Avoid repeating the same introduction in every response. Be concise, structured, and helpful."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

# Local model call (Ollama)
def ask_local_model(messages):
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3",
                "messages": messages,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logging.error(f"Error calling local model: {e}")
        return "Sorry, I couldn't generate a response at the moment."

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("frontend/index.html")

@app.get("/commit_failures.html", response_class=HTMLResponse)
async def commit_failures_page():
    return FileResponse("frontend/commit_failures.html")

@app.get("/resolution.html", response_class=HTMLResponse)
async def resolution_page():
    return FileResponse("frontend/resolution.html")

release_to_commit = {
    "9.0.0": "de455822b3467ca0b5805570c057123c4c859018",
    "9.0.1": "eb87c18471a734d7cd31e64ed3c8c14b1e907dc9",
    "9.0.2": "4282c85b9e4ecbd2efaa13dfbf7b0bc591f569c3",
    "9.0.3": "ee11d5834df9f4e3e0bc7311eb3ab37eed612afb",
    "9.0.4": "338577bf3456a2cadeec85b45e00f319e87bcabf",
    "9.0.5": "5501324ffb0c52b594cb164e8b93375588662468",
    "9.0.6": "82020f7ffaad11c15f6fc7beacdf4fc79c326ace",
    "9.0.7": "ca85f2e65d903f93f60eb97b3ff1209992df0eae"
}


@app.post("/commit_failures")
async def get_commit_failures(request: Request):
    body = await request.json()
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    user_input = body.get("commit_id", "").strip()
    author_name_query = body.get("author_name", "").strip().lower()

    # Helper to parse date string
    def parse_date(date_str):
        try:
            return date_str and date_str[:10]
        except Exception:
            return None

    # --- Test Center Results ---
    flat_data = [item for sublist in combined_data for item in sublist]
    test_center_matches = []
    # --- Jenkins Results (final_base.json & final_quick.json) ---
    def load_json_file(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    jenkins_base = load_json_file("final_base.json")
    jenkins_quick = load_json_file("final_quick.json")
    jenkins_base_matches = []
    jenkins_quick_matches = []


    # Author name search (takes precedence if provided)
    if author_name_query:
        def author_match(name):
            if not name:
                return False
            return author_name_query in name.lower()

        test_center_matches = [
            {
                "Source": "Test Center",
                "Revision": row.get("Revision"),
                "Date": row.get("Date"),
                "Type": row.get("Type"),
                "Status": row.get("Status"),
                "Total": row.get("Total"),
                "Failures": row.get("Failures"),
                "Garbage": row.get("Garbage"),
                "id_href": row.get("id_href"),
                "Platform": row.get("Platform", "Test Center"),
                "author_name": row.get("author_name"),
                "author_email": row.get("author_email")
            }
            for row in flat_data
            if author_match(row.get("author_name"))
        ]

        def match_jenkins(data):
            return [
                {
                    "Source": "Jenkins",
                    "Revision": item.get("commit"),
                    "Date": item.get("date"),
                    "Type": item.get("Type"),
                    "Status": item.get("Status"),
                    "Total": item.get("total"),
                    "Passed": item.get("passed"),
                    "Failed": item.get("failed"),
                    "Skipped": item.get("skipped"),
                    "URL": item.get("URL"),
                    "Platform": item.get("Platform", "Jenkins"),
                    "author_name": item.get("author_name"),
                    "author_email": item.get("author_email")
                }
                for item in data
                if author_match(item.get("author_name"))
            ]
        jenkins_base_matches = match_jenkins(jenkins_base)
        jenkins_quick_matches = match_jenkins(jenkins_quick)
        all_matches = test_center_matches + jenkins_base_matches + jenkins_quick_matches
        return {"matches": all_matches}

    if start_date or end_date:
        # Support single date or range
        s_date = start_date or end_date
        e_date = end_date or start_date
        def in_range(date_str):
            try:
                return s_date <= date_str[:10] <= e_date
            except Exception:
                return False

        test_center_matches = [
            {
                "Source": "Test Center",
                "Revision": row.get("Revision"),
                "Date": row.get("Date"),
                "Type": row.get("Type"),
                "Status": row.get("Status"),
                "Total": row.get("Total"),
                "Failures": row.get("Failures"),
                "Garbage": row.get("Garbage"),
                "id_href": row.get("id_href"),
                "Platform": row.get("Platform", "Test Center"),
                "author_name": row.get("author_name"),
                "author_email": row.get("author_email")
            }
            for row in flat_data
            if row.get("Date") and in_range(row.get("Date"))
        ]

        def match_jenkins(data):
            return [
                {
                    "Source": "Jenkins",
                    "Revision": item.get("commit"),
                    "Date": item.get("date"),
                    "Type": item.get("Type"),
                    "Status": item.get("Status"),
                    "Total": item.get("total"),
                    "Passed": item.get("passed"),
                    "Failed": item.get("failed"),
                    "Skipped": item.get("skipped"),
                    "URL": item.get("URL"),
                    "Platform": item.get("Platform", "Jenkins"),
                    "author_name": item.get("author_name"),
                    "author_email": item.get("author_email")
                }
                for item in data
                if item.get("date") and in_range(item.get("date"))
            ]
        jenkins_base_matches = match_jenkins(jenkins_base)
        jenkins_quick_matches = match_jenkins(jenkins_quick)

    else:
        # Filter by commit id or release
        if not user_input:
            return {"matches": []}

        is_commit_id = any(c in user_input for c in "abcdef0123456789") and len(user_input) >= 7
        if is_commit_id:
            commit_id = user_input
        else:
            commit_id = release_to_commit.get(user_input)
            if not commit_id:
                return {"matches": []}

        test_center_matches = [
            {
                "Source": "Test Center",
                "Revision": row.get("Revision"),
                "Date": row.get("Date"),
                "Type": row.get("Type"),
                "Status": row.get("Status"),
                "Total": row.get("Total"),
                "Failures": row.get("Failures"),
                "Garbage": row.get("Garbage"),
                "id_href": row.get("id_href"),
                "Platform": row.get("Platform", "Test Center"),
                "author_name": row.get("author_name"),
                "author_email": row.get("author_email")
            }
            for row in flat_data
            if row.get("Revision") == commit_id or row.get("Revision", "")[:7] == commit_id[:7]
        ]

        def match_jenkins(data):
            return [
                {
                    "Source": "Jenkins",
                    "Revision": item.get("commit"),
                    "Date": item.get("date"),
                    "Type": item.get("Type"),
                    "Status": item.get("Status"),
                    "Total": item.get("total"),
                    "Passed": item.get("passed"),
                    "Failed": item.get("failed"),
                    "Skipped": item.get("skipped"),
                    "URL": item.get("URL"),
                    "Platform": item.get("Platform", "Jenkins"),
                    "author_name": item.get("author_name"),
                    "author_email": item.get("author_email")
                }
                for item in data
                if item.get("commit") == commit_id or item.get("commit", "")[:7] == commit_id[:7]
            ]
        jenkins_base_matches = match_jenkins(jenkins_base)
        jenkins_quick_matches = match_jenkins(jenkins_quick)

    all_matches = test_center_matches + jenkins_base_matches + jenkins_quick_matches
    return {"matches": all_matches}

@app.post("/search")
async def search_error(request: Request):
    body = await request.json()
    query = body.get("query", "")
    query_vec = model.encode([query], normalize_embeddings=True)
    D, I = index.search(np.array(query_vec), k=30)

    results = []
    for idx in I[0]:
        ticket = metadata[idx]
        results.append({
            "id": ticket["ID"],
            "title": ticket["Title"],
            "url": ticket["URL"],
            "status": ticket.get("Status", "Unknown")
        })
    return {"matches": results}

@app.post("/jenkins_chat")
async def jenkins_chats(request: Request):
    body = await request.json()
    user_messages = body.get("messages", [])

    if not user_messages or not isinstance(user_messages, list):
        return {"error": "A list of messages is required for multi-turn conversation."}
    for msg in user_messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            return {"error": "Each message must be a dict with 'role' and 'content' keys."}

    # Use only the latest user message
    latest_user_msg = next((msg["content"] for msg in reversed(user_messages) if msg["role"] == "user"), "")
    if not latest_user_msg:
        return {"error": "No user message found."}

    msg_lower = latest_user_msg.lower()

    # Intent detection
    is_greeting = any(word in msg_lower for word in greeting_keywords)
    is_jenkins_related = any(word in msg_lower for word in jenkins_keywords)

    if not is_greeting and not is_jenkins_related:
        return {
            "response": "I'm focused on Jenkins. Please ask something related to Jenkins tasks or configuration."
        }

    # Embed and retrieve relevant Jenkins docs
    query_vec = model.encode([latest_user_msg], normalize_embeddings=True)
    D, I = jenkins_index.search(np.array(query_vec), k=5)
    top_chunks = [jenkins_chunks[i] for i in I[0]]

    # Build prompt with only the latest user message and context
    prompt_messages = build_prompt_with_context(latest_user_msg, top_chunks)
    response = ask_local_model(prompt_messages)
    return {"response": response}





# --- BEGIN: Logic from test_llm_copy.py for /resolve_error_chat ---
RESOLUTION_SYSTEM_PROMPT = (
    "You are a UT failure assistant. You help users debug and fix errors in their code and unit tests in Python. "
    "If the user's question is related to the provided context, use it to answer. Don't mention the context in the response. "
    "If the question is not related to the context, answer as a general helpful LLM assistant, ignoring the context."
)
RESOLUTION_SENTENCE_MODEL = "BAAI/bge-large-en-v1.5"
RESOLUTION_FAISS_INDEX = "chunk.index"
RESOLUTION_CHUNK_TEXTS = "chunk_texts.json"

resolution_embedding_model = None
def get_resolution_embedding(text):
    global resolution_embedding_model
    if resolution_embedding_model is None:
        resolution_embedding_model = SentenceTransformer(RESOLUTION_SENTENCE_MODEL)
    emb = resolution_embedding_model.encode(text, normalize_embeddings=True)
    return emb if isinstance(emb, np.ndarray) else np.array(emb, dtype=np.float32)

def get_most_relevant_resolution_chunk(user_input, faiss_index_path=RESOLUTION_FAISS_INDEX, chunk_texts_path=RESOLUTION_CHUNK_TEXTS, threshold=0.5, top_k=3):
    try:
        index = faiss.read_index(faiss_index_path)
        with open(chunk_texts_path, "r") as f:
            chunk_texts = json.load(f)
        user_emb = get_resolution_embedding("Question: " + user_input).reshape(1, -1)
        faiss.normalize_L2(user_emb)
        D, I = index.search(user_emb, top_k)
        best_idx = int(I[0][0])
        best_score = float(D[0][0])
        if best_score >= threshold:
            return chunk_texts[best_idx]["text"]
        else:
            return None
    except Exception:
        return None


# Azure OpenAI configuration (load API key from .env)
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_ENDPOINT = "https://hackfest25.openai.azure.com/"
AZURE_API_VERSION = "2025-01-01-preview"
AZURE_DEPLOYMENT = "gpt-4o"
azure_client = AzureOpenAI(api_key=AZURE_API_KEY, azure_endpoint=AZURE_ENDPOINT, api_version=AZURE_API_VERSION)

def query_azure_gpt_resolve(prompt, reference_text=None, message_history=None):
    messages = []
    if message_history:
        messages.extend(message_history)
    else:
        messages.append({"role": "system", "content": RESOLUTION_SYSTEM_PROMPT})
    if reference_text:
        user_content = f"Context:\n{reference_text}\n\nUser question: {prompt}"
    else:
        user_content = prompt
    messages.append({"role": "user", "content": user_content})
    try:
        response = azure_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=messages
        )
        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        return f"Error communicating with Azure OpenAI: {e}"

@app.post("/resolve_error_chat")
async def resolve_error_chat(request: Request):
    body = await request.json()
    user_messages = body.get("messages", [])
    if not user_messages or not isinstance(user_messages, list):
        return {"error": "A list of messages is required for multi-turn conversation."}
    for msg in user_messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            return {"error": "Each message must be a dict with 'role' and 'content' keys."}

    # Find the latest user message
    latest_user_msg = next((msg["content"] for msg in reversed(user_messages) if msg["role"] == "user"), "")
    if not latest_user_msg:
        return {"error": "No user message found."}

    # Find the most relevant chunk
    relevant_chunk = get_most_relevant_resolution_chunk(latest_user_msg)

    # If user asks a follow-up, use last relevant chunk (not tracked in stateless API, so just use current)
    # Compose message history for Azure GPT
    message_history = [
        {"role": "system", "content": RESOLUTION_SYSTEM_PROMPT}
    ]
    for msg in user_messages:
        if msg["role"] == "user":
            message_history.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            message_history.append({"role": "assistant", "content": msg["content"]})

    if relevant_chunk is not None:
        reply = query_azure_gpt_resolve(latest_user_msg, reference_text=relevant_chunk, message_history=message_history)
    else:
        reply = query_azure_gpt_resolve(latest_user_msg, reference_text=None, message_history=message_history)
    return {"response": reply}
