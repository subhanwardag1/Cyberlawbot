"""
CyberLaw Bot — Pakistan Legal RAG Assistant
FastAPI server wrapping the existing RAG pipeline with a web frontend.
"""
import sys
import os
import uuid
import time
import json
import hashlib
import base64
import struct
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from collections import OrderedDict

# ── Console encoding: let Urdu/Arabic be logged on Windows (cp1252) consoles ──
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Path setup ──
SCRIPT_DIR = Path(__file__).parent.resolve()   # the Backend folder
FYP_DIR = SCRIPT_DIR.parent                    # the project root
sys.path.insert(0, str(SCRIPT_DIR))

from rag_pipeline import query_and_answer, GEMINI_API_KEY

# ── App ──
app = FastAPI(
    title="CyberLaw Bot",
    description="AI-powered CyberLaw Bot",
    version="1.0.0",
    docs_url=None,        # /docs disabled: no public API schema disclosure
    openapi_url=None,     # /openapi.json disabled for the same reason
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cyberlawbot.onrender.com",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers on every response ──
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response


# ── Conversation memory (in-memory, per session) ──
conversation_sessions: Dict[str, List[Dict[str, str]]] = {}

# ── Query rate limit (protects Gemini quota from abuse) ──
QUERY_RATE_LIMIT = int(os.environ.get("QUERY_RATE_LIMIT", 30))  # requests/min per client
_query_rate: Dict[str, List[float]] = {}


def _query_allowed(client_ip: str) -> bool:
    now = time.time()
    win = [t for t in _query_rate.get(client_ip, []) if now - t < 60]
    if len(win) >= QUERY_RATE_LIMIT:
        _query_rate[client_ip] = win
        return False
    win.append(now)
    _query_rate[client_ip] = win
    return True


# ── Models ──
class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(6, ge=1, le=20)  # bounded so retrieval can't be abused
    session_id: Optional[str] = None
    language: Optional[str] = "en"  # "en" or "ur" - from the UI language toggle


class FeedbackRequest(BaseModel):
    vote: int  # 1 = helpful, -1 = not helpful
    question: Optional[str] = None  # hashed before storage; never stored raw


# ── Routes ──

@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse(FYP_DIR / "Frontend" / "index.html")


@app.post("/api/query")
async def handle_query(request: QueryRequest, http_req: Request):
    """Process a legal question through the RAG pipeline with conversation memory."""
    client_ip = http_req.client.host if http_req.client else "unknown"
    if not _query_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many questions right now. Please wait a moment.")
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []
    
    history = conversation_sessions[session_id]

    try:
        t0 = time.perf_counter()
        result = query_and_answer(
            question,
            db_dir=str(FYP_DIR / "vector_db"),
            top_k=request.top_k,
            conversation_history=history,
            language=request.language or "en",
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        
        # Store the exchange in session history
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": result["answer"]})
        
        # Keep history bounded (last 20 turns = 10 exchanges)
        if len(history) > 20:
            conversation_sessions[session_id] = history[-20:]
        
        return {
            "answer": result["answer"],
            "references": result["references"],
            "retrieved": result["retrieved"],
            "session_id": session_id,
            "elapsed_ms": elapsed_ms,
            "helplines": result.get("helplines", []),
            "complaint": result.get("complaint"),
            "language": result.get("language", "en"),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Vector database not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


@app.post("/api/reset")
async def reset_session(request: dict = {}):
    """Clear conversation history for a session."""
    session_id = request.get("session_id")
    if session_id and session_id in conversation_sessions:
        del conversation_sessions[session_id]
    return {"status": "ok", "message": "Session cleared"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    db_exists = (FYP_DIR / "vector_db" / "law_kb.json").exists()
    return {"status": "ok", "database_loaded": db_exists}


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Store a minimal, non-PII feedback record: vote + timestamp + a one-way
    hash of the question. No accounts, no raw question text, no identifiers."""
    vote = 1 if request.vote > 0 else (-1 if request.vote < 0 else 0)
    q_hash = None
    if request.question:
        q_hash = hashlib.sha256(request.question.encode("utf-8")).hexdigest()[:16]
    record = {"ts": int(time.time()), "vote": vote, "q_hash": q_hash}
    try:
        with open(FYP_DIR / "feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not store feedback: {e}")
    return {"status": "ok", "recorded": record}


# ── Serve PDF files for reference links ──
PDF_DIR = SCRIPT_DIR  # the four statute PDFs live next to this file


@app.get("/files/data/{filename:path}")
async def serve_pdf(filename: str):
    """Serve PDF files so users can view cited sources.

    A {filename:path} converter accepts slashes, so the joined path is resolved and
    must stay inside PDF_DIR. Anything that escapes it (for example ../../x.pdf) is
    rejected with 400 instead of being read from disk.
    """
    file_path = (PDF_DIR / filename).resolve()
    if not file_path.is_relative_to(PDF_DIR):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if file_path.is_file() and file_path.suffix.lower() == ".pdf":
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=file_path.name,
        )
    raise HTTPException(status_code=404, detail="File not found")


# Mount static files LAST so named routes take priority
# ── Server-side TTS (Gemini) so Urdu answers can be spoken on any device ──
# Future scope: costs Gemini API credits, so it is OFF unless TTS_ENABLED=1.
TTS_ENABLED = os.environ.get("TTS_ENABLED", "0") == "1"
TTS_MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Kore")
TTS_MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", 600))
TTS_RATE_LIMIT = int(os.environ.get("TTS_RATE_LIMIT", 12))  # requests/min per client
TTS_CACHE_MAX = int(os.environ.get("TTS_CACHE_MAX", 40))

_tts_cache: "OrderedDict[str, bytes]" = OrderedDict()
_tts_rate: Dict[str, List[float]] = {}
# Direct connection (no system proxy): proxies often break the TLS stream to Gemini.
_tts_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class TtsRequest(BaseModel):
    text: str
    language: Optional[str] = "en"


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    """Wrap raw 16-bit mono PCM (Gemini TTS output) in a WAV container."""
    channels, bits = 1, 16
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate, byte_rate, block_align, bits)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm


def _cap_text(text: str, limit: int) -> str:
    """Trim to a sentence boundary so audio stays short and fast to generate."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("۔", ".", "!", "?", "\n"):
        idx = cut.rfind(sep)
        if idx > limit // 2:
            return cut[: idx + 1].strip()
    return cut.strip()


def _tts_allowed(client_ip: str) -> bool:
    now = time.time()
    window = _tts_rate.setdefault(client_ip, [])
    while window and now - window[0] > 60:
        window.pop(0)
    if len(window) >= TTS_RATE_LIMIT:
        return False
    window.append(now)
    return True


@app.post("/api/tts")
def text_to_speech(req: TtsRequest, request: Request):
    if not TTS_ENABLED:
        raise HTTPException(status_code=503, detail="Urdu audio is disabled (future feature).")
    client_ip = request.client.host if request.client else "unknown"
    if not _tts_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many audio requests. Please wait a moment.")

    text = _cap_text((req.text or "").strip(), TTS_MAX_CHARS)
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    cache_key = hashlib.sha256(f"{TTS_MODEL}|{TTS_VOICE}|{text}".encode("utf-8")).hexdigest()[:16]
    if cache_key in _tts_cache:
        _tts_cache.move_to_end(cache_key)
        return Response(content=_tts_cache[cache_key], media_type="audio/wav",
                        headers={"X-TTS-Cache": "hit"})

    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": TTS_VOICE}}
            },
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent"
    http_req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
        method="POST",
    )
    last_err = None
    data = None
    for attempt in range(3):  # retry transient TLS/network flakes
        try:
            with _tts_opener.open(http_req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    if data is None:
        raise HTTPException(status_code=502, detail=f"TTS upstream error: {last_err}")

    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    b64 = None
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data") or {}
        if inline.get("data"):
            b64 = inline["data"]
            break
    if not b64:
        raise HTTPException(status_code=502, detail="TTS returned no audio")

    wav = _pcm_to_wav(base64.b64decode(b64))
    _tts_cache[cache_key] = wav
    _tts_cache.move_to_end(cache_key)
    while len(_tts_cache) > TTS_CACHE_MAX:
        _tts_cache.popitem(last=False)
    return Response(content=wav, media_type="audio/wav", headers={"X-TTS-Cache": "miss"})


app.mount("/static", StaticFiles(directory=str(FYP_DIR / "Frontend")), name="static")


# ── Entry point ──
if __name__ == "__main__":
    print()
    print("=" * 56)
    print("  CyberLaw Bot")
    print("=" * 56)
    print()
    print(f"  Open in browser:  http://localhost:8000")
    print(f"  Vector DB:        {FYP_DIR / 'vector_db'}")
    print(f"  PDF sources:      {PDF_DIR}")
    print()
    print("  Press Ctrl+C to stop.\n")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
