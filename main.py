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
    user_input = body.get("commit_id", "").strip()

    if not user_input:
        return {"matches": []}

    is_commit_id = any(c in user_input for c in "abcdef0123456789") and len(user_input) >= 7
    if is_commit_id:
        commit_id = user_input
    else:
        commit_id = release_to_commit.get(user_input)
        if not commit_id:
            return {"matches": []}

    flat_data = [item for sublist in combined_data for item in sublist]
    matching_rows = [
        row for row in flat_data
        if row.get("Revision") == commit_id or row.get("Revision", "")[:7] == commit_id[:7]
    ]
    return {"matches": matching_rows}

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




@app.post("/resolve_error_chat")
async def resolve_error_chat(request: Request):
    body = await request.json()
    user_messages = body.get("messages", [])

    if not user_messages or not isinstance(user_messages, list):
        return {"error": "A list of messages is required for multi-turn conversation."}
    for msg in user_messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            return {"error": "Each message must be a dict with 'role' and 'content' keys."}

    system_prompt = {
        "role": "system",
        "content": "You are a helpful assistant that provides detailed solutions to Unit Test Failures. Ask clarifying questions if needed and guide the user to resolve their error."
    }
    full_conversation = [system_prompt] + user_messages

    api_key = os.getenv("API_KEY")
    try:
        API_URL = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-4-maverick:free",
            "messages": full_conversation,
            "max_tokens": 4096
        }
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        logging.error(f"Error in resolve_error_chat: {str(e)}")
        return {"error": str(e)}
