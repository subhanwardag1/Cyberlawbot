import os
import json
import re
import numpy as np
from pathlib import Path
import google.generativeai as genai

# Load .env for local development (real environment variables take precedence).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure Gemini API ONCE at module level
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set!")
genai.configure(api_key=GEMINI_API_KEY)

# ── Cached database (loaded once, reused across queries) ──
_cached_documents = None
_cached_embeddings = None
_cached_db_dir = None


# Generation model. gemini-2.5-flash runs in "thinking" mode (~13s/answer) and the
# deprecated google-generativeai SDK (0.8.6) cannot disable it. gemini-flash-lite-latest
# has no thinking mode and answers in ~2s, keeping the full pipeline under the 5s demo
# target while staying accurate at grounded legal synthesis. The "-latest" alias also
# avoids the 404s that retired pinned names (gemini-2.0-flash, gemini-2.5-flash-lite)
# now return. Swap to "gemini-2.5-flash" only if you prefer max reasoning over speed.
GENERATION_MODEL = "gemini-flash-lite-latest"

# Optional latency trim (only applies if you switch back to a thinking model AND
# upgrade to the new google-genai SDK). Harmless no-op with the current SDK.
DISABLE_THINKING = True


def _generation_config():
    if not DISABLE_THINKING:
        return None
    try:
        from google.generativeai import types
        return types.GenerationConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
    except Exception:
        return None


def _generate(model, prompt):
    """generate_content with a safe fallback if the thinking config is unsupported."""
    cfg = _generation_config()
    if cfg is not None:
        try:
            return model.generate_content(prompt, generation_config=cfg)
        except Exception:
            pass  # fall back to a plain call below
    return model.generate_content(prompt)


# ── Emergency / high-severity flagging ──
# Numbers verified against official sources (FIA/NR3C, Madadgaar, PCSW, Punjab
# Child Protection Bureau). CONFIRM they are current before the demo.
HELPLINES = [
    {"name": "Police Emergency", "number": "15",
     "note": "Immediate danger, anywhere in Pakistan"},
    {"name": "Rescue", "number": "1122",
     "note": "Emergency medical / rescue"},
    {"name": "FIA Cyber Crime Wing (NR3C)", "number": "051-111-345-786",
     "note": "Report cybercrime, online harassment, blackmail; also complaint.fia.gov.pk"},
    {"name": "Madadgaar National Helpline", "number": "1098",
     "note": "Toll-free, 24/7 - women & child protection"},
    {"name": "Women's Helpline (PCSW)", "number": "1043",
     "note": "24/7 support for women"},
    {"name": "Child Protection Helpline", "number": "1121",
     "note": "A child at risk"},
]

# Keywords signalling an urgent or high-severity situation (English + Urdu).
_URGENCY_KEYWORDS = [
    # cyber-harassment / coercion
    "blackmail", "extort", "extortion", "sextortion", "revenge porn", "revenge-porn",
    "nude", "nudes", "intimate image", "intimate images", "leak my", "leaked my",
    "cyber harass", "cyberharass", "online harass", "harass", "harassing", "harassment",
    "stalk", "stalking", "stalker", "threat", "threaten", "threatening", "death threat",
    "doxx", "doxxing", "hacked", "account hack", "hack my",
    # physical / sexual violence
    "rape", "sexual assault", "molest", "molestation", "assault", "beat me", "beating",
    "kidnap", "kidnapping", "abduct", "abduction", "kill me", "murder me",
    "domestic violence", "child abuse", "abuse me", "abusing me", "abused",
    # minors
    "underage", "under-age", "under 18", "juvenile", "minor girl", "minor boy", "a minor",
    # self-harm
    "suicide", "suicidal", "kill myself", "end my life", "self harm", "self-harm",
    # Urdu
    "بلیک میل", "دھمکی", "ہراسانی", "ہراس", "زیادتی", "عصمت دری", "اغوا",
    "خودکشی", "تشدد", "جان سے مار", "نا بالغ",
]


def detect_urgency(question: str) -> bool:
    """Return True when a question signals an emergency or high-severity situation."""
    if not question:
        return False
    q = question.lower()
    return any(kw in q for kw in _URGENCY_KEYWORDS)


# Keywords signalling a reportable cyber offence (broader than urgency): the user
# is likely to benefit from a direct link to the official complaint form.
_COMPLAINT_KEYWORDS = [
    # English
    "cybercrime", "cyber crime", "cyber-crime", "fraud", "cheat", "cheating", "scam",
    "phishing", "spoof", "identity theft", "impersonat", "fake account", "fake profile",
    "defamation", "defame", "obscene", "vulgar", "morph", "blackmail", "extort",
    "harass", "harassment", "stalk", "threat", "hack", "hacked", "unauthorized access",
    "data breach", "privacy breach", "my photo", "my pictures", "my video",
    "complaint", "report", "file a case", "fir",
    # Urdu
    "سائبر کرائم", "فراڈ", "جعلسازی", "دھوکہ", "فشنگ", "جعلی اکاؤنٹ", "جعلی پروفائل",
    "ہراسانی", "ہراس", "بلیک میل", "دھمکی", "غیر اخلاقی", "فحش", "مرف",
    "تصاویر", "ویڈیو", "پرائیویسی", "ڈیٹا چوری", "ہیک", "شکایت", "رپورٹ", "مقدمہ",
]

# Official government complaint portal (env-tunable so it can be swapped easily).
COMPLAINT_URL = os.environ.get("COMPLAINT_URL", "https://complaint.fia.gov.pk/")
COMPLAINT = {"name": "FIA / NCCIA Online Complaint", "url": COMPLAINT_URL}


def detect_complaint(question: str) -> bool:
    """True when the question describes a reportable cyber offence."""
    if not question:
        return False
    q = question.lower()
    return any(kw in q for kw in _COMPLAINT_KEYWORDS)


# Urdu/Arabic script detection (drives cross-lingual retrieval + RTL rendering).
_URDU_SCRIPT_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')


def has_urdu_script(text: str) -> bool:
    """True when a meaningful share of the text is Urdu/Arabic script."""
    if not text:
        return False
    urdu_chars = len(_URDU_SCRIPT_RE.findall(text))
    return urdu_chars > 0 and urdu_chars >= len(text.strip()) * 0.3


def load_vector_db(db_dir="vector_db", collection_name="law_kb"):
    """
    Load the vector database. Uses an in-memory cache so it's only
    read from disk once per session, not on every question.
    """
    global _cached_documents, _cached_embeddings, _cached_db_dir
    
    # Return cached version if already loaded from the same directory
    if _cached_documents is not None and _cached_db_dir == db_dir:
        return _cached_documents, _cached_embeddings
    
    db_path = Path(db_dir)
    db_file = db_path / f"{collection_name}.json"
    embeddings_file = db_path / "embeddings.npy"
    
    if not db_file.exists():
        raise FileNotFoundError(f"Vector database not found at {db_file}")
    
    # Load documents (text + metadata)
    with open(db_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    # Load embeddings — prefer .npy (fast), fall back to reading from JSON
    if embeddings_file.exists():
        embeddings = np.load(embeddings_file)
    elif documents and "embedding" in documents[0]:
        # Legacy format: embeddings stored inside JSON
        embeddings = np.array([doc["embedding"] for doc in documents], dtype=np.float32)
    else:
        raise FileNotFoundError(f"Embeddings not found at {embeddings_file}")
    
    # Pre-compute norms for vectorized cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # avoid division by zero
    normalized_embeddings = embeddings / norms
    
    # Cache everything
    _cached_documents = documents
    _cached_embeddings = normalized_embeddings
    _cached_db_dir = db_dir
    
    return documents, normalized_embeddings


def search_similar_documents(query_embedding, normalized_embeddings, documents, top_k=4):
    """
    Search for similar documents using vectorized cosine similarity.
    All documents are compared in a single NumPy operation — ~100x faster than a Python loop.
    """
    query_vec = np.array(query_embedding, dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []
    query_vec = query_vec / query_norm
    
    # Single matrix-vector multiplication for ALL similarities at once
    similarities = normalized_embeddings @ query_vec
    
    # Get top-k indices using argpartition (faster than full sort for large arrays)
    if len(similarities) <= top_k:
        top_indices = np.argsort(similarities)[::-1]
    else:
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
    
    results = []
    for idx in top_indices:
        results.append({
            "text": documents[idx]["text"],
            "metadata": documents[idx]["metadata"],
            "similarity": float(similarities[idx]),
            "distance": 1.0 - float(similarities[idx])
        })
    
    return results


def get_query_embedding(question):
    """
    Generate embedding for a question using Gemini API.
    """
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=question,
        task_type="retrieval_query"
    )
    return result['embedding']


def rewrite_followup_query(question, conversation_history):
    """
    Produce ONE English, standalone search query for retrieval.

    Does two jobs in a single Gemini call, and only when needed:
    - Translates Urdu questions into English (the vector KB is English-only, so a
      raw Urdu query embeds weakly and retrieves poorly).
    - Resolves vague follow-ups ("and for X?") using the conversation history.
    With no history and an already-English question it returns as-is (no API call).
    """
    is_urdu = has_urdu_script(question)
    if not conversation_history and not is_urdu:
        return question

    # Build a concise history string (last 6 turns max to stay within limits)
    history_text = ""
    for turn in conversation_history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        # Truncate long assistant responses to keep the rewrite prompt small
        if role == "assistant" and len(content) > 500:
            content = content[:500] + "..."
        history_text += f"{role.upper()}: {content}\n"

    rewrite_prompt = f"""Rewrite the user's message into ONE clear, standalone legal search query IN ENGLISH that can be matched against English statute text.

Rules:
- The output MUST be in English. If the message is in Urdu, translate it to English.
- Resolve any follow-up references (like "it", "that", "and for X?") using the conversation history.
- Keep it to a single concise search sentence. Return ONLY the query, nothing else.

Conversation History:
{history_text or '(none)'}

User Message: {question}

English standalone search query:"""

    try:
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = _generate(model, rewrite_prompt)
        rewritten = response.text.strip()
        if rewritten:
            print(f"[*] Rewritten query: {rewritten}")
            return rewritten
    except Exception as e:
        print(f"[WARN] Query rewrite failed, using original: {e}")

    return question


def query_and_answer(question, db_dir="vector_db", top_k=6, max_context_chars=8000, conversation_history=None, language="en"):
    """
    Query the vector database and generate an answer using Gemini API.
    
    Optimizations applied:
    - DB is cached in memory (loaded once per session)
    - Vectorized similarity search (~100x faster)
    - Increased context window for better answers (8000 chars)
    - API configured once at module level
    - Conversation history support for follow-up questions
    """
    if conversation_history is None:
        conversation_history = []
    
    print(f"[*] Processing question: {question}")
    print(f"[*] Conversation history length: {len(conversation_history)} turns")
    
    # Answer language is driven by the user's explicit UI toggle ("en"/"ur").
    language = "ur" if str(language).lower().startswith("ur") else "en"

    # Rewrite follow-up questions into standalone queries for better retrieval
    # (also translates Urdu -> English so it matches the English-only KB).
    search_query = rewrite_followup_query(question, conversation_history)
    
    # Load vector database (cached after first call)
    print(f"[*] Loading vector database from {db_dir}...")
    documents, normalized_embeddings = load_vector_db(db_dir)
    print(f"[OK] Loaded {len(documents)} documents")
    
    # Generate embedding for the REWRITTEN question (better retrieval)
    print(f"[*] Generating question embedding...")
    try:
        query_embedding = get_query_embedding(search_query)
    except Exception as e:
        print(f"[ERROR] Failed to generate embedding: {e}")
        return {"answer": "Error generating embedding", "references": [], "retrieved": []}
    
    # Search for similar documents (vectorized)
    print(f"[*] Searching for similar documents...")
    similar_docs = search_similar_documents(query_embedding, normalized_embeddings, documents, top_k)
    
    # Build context from retrieved documents
    ctx_parts = []
    total = 0
    for d in similar_docs:
        md = d["metadata"]
        ref = f"{md.get('law')} - {md.get('section')}"
        snippet = d["text"]
        part = f"[{ref}] (Source: {md.get('source')}, page: {md.get('page')})\n{snippet}\n"
        if total + len(part) > max_context_chars:
            break
        ctx_parts.append(part)
        total += len(part)
    
    context = "\n---\n".join(ctx_parts)
    
    # Build conversation history string for the prompt
    history_text = ""
    if conversation_history:
        recent = conversation_history[-6:]  # Last 6 turns to avoid token overflow
        history_parts = []
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            # Truncate long assistant responses
            if role == "assistant" and len(content) > 800:
                content = content[:800] + "..."
            label = "User" if role == "user" else "Assistant"
            history_parts.append(f"{label}: {content}")
        history_text = "\n".join(history_parts)
    
    # Generate answer using Gemini
    print(f"[*] Generating answer using Gemini...")
    
    is_urgent = detect_urgency(question)
    urgency_note = (
        "\nThe user may be dealing with an urgent or distressing situation. Stay factual and calm, "
        "and encourage them to contact the relevant authorities or a helpline (surfaced to them separately).\n\n"
        if is_urgent else ""
    )

    if language == "ur":
        language_rule = (
            "- LANGUAGE: Reply ENTIRELY in Urdu, using Urdu script (Nastaliq). Do NOT use Roman Urdu, "
            "do NOT write any sentence in English, and do NOT mix languages. Use proper Urdu legal "
            "terminology. You may keep statute names and section numbers in their standard form "
            "(for example 'PECA 2016', 'Section 302' or 'دفعہ 302'), but every explanatory "
            "sentence must be in Urdu script."
        )
    else:
        language_rule = "- LANGUAGE: Reply entirely in clear, professional English."

    if history_text:
        prompt = f"""You are "CyberLaw Bot", a precise legal assistant for Pakistani criminal law. Write like a clear, experienced lawyer advising a layperson: direct, professional, and practical.

IMPORTANT RULES FOR YOUR TONE:
- Answer the user's question DIRECTLY first (e.g., "Yes, you should..." or "No, that would not be advisable because...")
- Then explain the legal basis in simple, easy-to-understand language
- Give practical, actionable advice (what to do step-by-step)
- Use the legal texts as SUPPORTING EVIDENCE for your advice — do NOT just summarize them
- Include citations naturally in your response like: (Pakistan Penal Code, Section 506)
{language_rule}
- Be direct and professional. NEVER greet the user, introduce yourself, apologize, or add filler (do not write "Hello", "Great question", "I'm CyberLaw Bot", or "I'm sorry"), and do not restate the question.
- Base your answer on the legal provisions below; if they do not cover the question, say so plainly instead of inventing citations.
- Be concise: about 120-220 words unless the question genuinely needs more.
- Connect your answer to the previous conversation naturally

Previous Conversation:
{history_text}

Relevant Legal Provisions:
{context}

User's Question: {question}

{urgency_note}Your response (start with the direct answer; no greetings or preamble):"""
    else:
        prompt = f"""You are "CyberLaw Bot", a precise legal assistant for Pakistani criminal law. Write like a clear, experienced lawyer advising a layperson: direct, professional, and practical.

IMPORTANT RULES FOR YOUR TONE:
- Answer the user's question DIRECTLY first (e.g., "Yes, you can..." or "Under Pakistani law, this means...")
- Then explain the legal basis in simple, easy-to-understand language
- Give practical, actionable advice when relevant (what to do, where to go, who to contact)
- Use the legal texts as SUPPORTING EVIDENCE for your advice — do NOT just summarize or list them
- Include citations naturally in your response like: (Pakistan Penal Code, Section 506)
{language_rule}
- Be direct and professional. NEVER greet the user, introduce yourself, apologize, or add filler (do not write "Hello", "Great question", "I'm CyberLaw Bot", or "I'm sorry"), and do not restate the question.
- Base your answer on the legal provisions below; if they do not cover the question, say so plainly instead of inventing citations.
- Be concise: about 120-220 words unless the question genuinely needs more.

Relevant Legal Provisions:
{context}

User's Question: {question}

{urgency_note}Your response (start with the direct answer; no greetings or preamble):"""
    
    try:
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = _generate(model, prompt)
        answer = response.text
    except Exception as e:
        print(f"[ERROR] Failed to generate answer: {e}")
        answer = f"Error generating answer: {e}"
    
    # Build references
    linked = []
    seen = set()
    for d in similar_docs:
        md = d["metadata"]
        label = f"{md.get('law')} - {md.get('section')}"
        pdf_file = md.get("source")
        page = md.get("page")
        url = f"/files/data/{pdf_file}#page={page}"
        if label not in seen:
            linked.append({"label": label, "url": url, "page": page, "pdf": pdf_file})
            seen.add(label)
    
    return {
        "answer": answer,
        "references": linked,
        "retrieved": [{
            "snippet": d["text"][:800],
            "metadata": d["metadata"],
            "similarity": d["similarity"]
        } for d in similar_docs],
        "helplines": HELPLINES if is_urgent else [],
        "complaint": COMPLAINT if detect_complaint(question) else None,
        "language": language,
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "What are the penalties for cybercrime under PECA?"
    
    print(f"\n{'='*60}")
    print(f"RAG Pipeline - Legal Question Answering")
    print(f"{'='*60}\n")
    
    result = query_and_answer(question, db_dir="vector_db", top_k=6)
    
    print(f"\n{'='*60}")
    print(f"ANSWER:")
    print(f"{'='*60}")
    print(result["answer"])
    
    print(f"\n{'='*60}")
    print(f"REFERENCES:")
    print(f"{'='*60}")
    for i, ref in enumerate(result["references"], 1):
        print(f"{i}. {ref['label']} (Page {ref['page']})")
    
    print(f"\n{'='*60}")
    print(f"RETRIEVED DOCUMENTS:")
    print(f"{'='*60}")
    for i, doc in enumerate(result["retrieved"], 1):
        print(f"\nDocument {i} (Similarity: {doc['similarity']:.4f}):")
        print(f"Law: {doc['metadata']['law']}")
        print(f"Section: {doc['metadata']['section']}")
        print(f"Snippet: {doc['snippet'][:200]}...")