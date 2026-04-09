import os
import json
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

from utils import clone_repo, cleanup_dir
from analyzer import analyze_repo
from gemini_client import generate_mermaid_and_explanation, chat_about_repo

app = FastAPI()

def init_db():
    conn = sqlite3.connect("cache.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS analysis_cache (
            repo_url TEXT,
            mode TEXT,
            mermaid_code TEXT,
            explanation TEXT,
            PRIMARY KEY (repo_url, mode)
        )
    ''')
    try:
        c.execute("ALTER TABLE analysis_cache ADD COLUMN context TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def get_from_cache(repo_url: str, mode: str):
    conn = sqlite3.connect("cache.db")
    c = conn.cursor()
    try:
        c.execute("SELECT mermaid_code, explanation, context FROM analysis_cache WHERE repo_url = ? AND mode = ?", (repo_url, mode))
    except sqlite3.OperationalError:
        c.execute("SELECT mermaid_code, explanation FROM analysis_cache WHERE repo_url = ? AND mode = ?", (repo_url, mode))
    row = c.fetchone()
    conn.close()
    if row:
        return {"mermaid_code": row[0], "explanation": row[1], "context": row[2] if len(row) > 2 else None}
    return None

def save_to_cache(repo_url: str, mode: str, mermaid_code: str, explanation: str, context: str = None):
    conn = sqlite3.connect("cache.db")
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO analysis_cache (repo_url, mode, mermaid_code, explanation, context)
        VALUES (?, ?, ?, ?, ?)
    ''', (repo_url, mode, mermaid_code, explanation, context))
    conn.commit()
    conn.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    repo_url: str
    mode: str = "default"

class AnalyzeResponse(BaseModel):
    mermaid_code: str
    explanation: str

class HistoryItem(BaseModel):
    repo_url: str
    mode: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    repo_url: str
    mode: str = "default"
    history: list[ChatMessage] = []
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.get("/history", response_model=list[HistoryItem])
def history_endpoint():
    conn = sqlite3.connect("cache.db")
    c = conn.cursor()
    c.execute("SELECT repo_url, mode FROM analysis_cache ORDER BY rowid DESC")
    rows = c.fetchall()
    conn.close()
    return [{"repo_url": r[0], "mode": r[1]} for r in rows]

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest):
    if not request.repo_url.startswith("https://") and not hasattr(request, "repo_url"):
        raise HTTPException(status_code=400, detail="Invalid repository URL")

    cached = get_from_cache(request.repo_url, request.mode)
    if cached and cached.get("context"):
        return AnalyzeResponse(
            mermaid_code=cached["mermaid_code"],
            explanation=cached["explanation"]
        )

    temp_dir = None
    try:
        temp_dir, target_dir, base_url, branch = clone_repo(request.repo_url)
        json_data = analyze_repo(target_dir, max_files=1000)
        
        if not json_data.get("file_tree"):
            raise HTTPException(status_code=400, detail="Repository is empty or no supported files found.")
            
        result = generate_mermaid_and_explanation(json_data, base_url, branch, request.mode)
        
        context_str = json.dumps(json_data)
        save_to_cache(request.repo_url, request.mode, result["mermaid_code"], result["explanation"], context_str)
        
        return AnalyzeResponse(
            mermaid_code=result["mermaid_code"],
            explanation=result["explanation"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir:
            cleanup_dir(temp_dir)

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    cached = get_from_cache(request.repo_url, request.mode)
    if not cached or not getattr(cached, "context", None) and not cached.get("context"):
        raise HTTPException(status_code=404, detail="Repository context not found. Please analyze the repository again to enable chat.")
    
    try:
        reply = chat_about_repo(cached["context"], [{"role": m.role, "content": m.content} for m in request.history], request.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

