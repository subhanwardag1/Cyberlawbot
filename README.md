# CyberLaw Bot

<img src="Frontend/logo.png" alt="CyberLaw Bot logo" width="110" align="right">

**CyberLaw Bot** is an AI-powered legal assistant for Pakistan. It answers questions about
Pakistani criminal law — in **English and Urdu** — and backs every answer with the exact
statute provisions it used, so any claim can be verified against the law itself.

Built for the **Bano Qabil National Hackathon**.

> ⚖️ **Disclaimer:** CyberLaw Bot provides legal *information*, not legal advice.
> Always consult a qualified lawyer for your specific situation.

---

## What it does

- **Grounded answers with citations** — every reply cites the exact act, section and page it
  was derived from, with a transparency panel showing the retrieved statute text.
- **Fully bilingual** — complete English / Urdu interface with right-to-left layout,
  Urdu question understanding and cross-lingual retrieval (ask in Urdu, retrieve English statutes).
- **Conversation memory** — follow-up questions ("what is the punishment for *it*?") are
  resolved against the ongoing session.
- **Safety first** — urgent situations (blackmail, harassment, threats) surface official
  helplines, and reportable cyber offences show a direct link to the official
  **FIA / NCCIA online complaint portal**.
- **Voice input** — speak your question in Chrome/Edge (HTTPS or localhost).
- **Anonymous feedback** — thumbs up/down stored as a one-way hash only; no accounts, no PII.

## Legal coverage

| Statute | Scope |
|---|---|
| Code of Criminal Procedure (CrPC) | procedure, bail, arrest, trials |
| Pakistan Penal Code (PPC) | offences and punishments |
| PECA 2016 | cybercrime: unauthorized access, cyberstalking, defamation, fraud |
| PECA 2025 Amendment | updated cyber offence definitions and penalties |

**2,373 indexed provisions** are embedded and searched for every question.

## How it works (RAG)

1. Your question is converted into a numerical embedding.
2. A **hand-built NumPy cosine-similarity vector index** (no LangChain, no external vector DB)
   retrieves the most relevant statute provisions.
3. Gemini receives *only* those provisions and writes a grounded answer, citing them.
4. The frontend renders the answer, citations, retrieval confidence and latency.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| Retrieval | Custom NumPy cosine vector search over 2,373 chunks |
| AI | Google Gemini (`gemini-flash-lite-latest`, `gemini-embedding-001`) |
| Frontend | Vanilla HTML / CSS / JavaScript (no framework), Web Speech API |
| Hosting | Render (HTTPS), custom domain |

## Project structure

```
├── Backend/
│   ├── server.py            # FastAPI app: /api/query, /api/health, /api/feedback, /api/tts
│   ├── rag_pipeline.py      # embedding, retrieval, prompting, urgency & complaint detection
│   ├── build_vector_db.py   # offline indexer: PDFs → chunks → embeddings
│   ├── extract_text.py      # PDF text extraction
│   └── *.pdf                # source statutes (CrPC, PPC, PECA 2016, PECA 2025)
├── Frontend/
│   ├── index.html           # app shell (EN/UR, RTL-aware)
│   ├── app.js               # chat, i18n dictionary, voice, citations, safety cards
│   ├── style.css            # light government-legal design system
│   └── logo.png             # brand mark
├── vector_db/
│   ├── embeddings.npy       # prebuilt embedding matrix (committed; never rebuilt on deploy)
│   └── law_kb.json          # chunk text + statute metadata
├── requirements.txt         # fully pinned dependencies
├── Procfile / render.yaml   # Render deployment descriptors
└── .env                     # local secrets (gitignored — never committed)
```

## Run it locally

**Prerequisites:** Python 3.11+, a Google Gemini API key.

```bash
pip install -r requirements.txt

# create .env in the project root
echo GEMINI_API_KEY=your_key_here > .env

python Backend/server.py
# → open http://localhost:8000
```

The vector database is committed, so no indexing step is needed.
To rebuild it from the PDFs: `python Backend/build_vector_db.py` (consumes embedding quota).

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/query` | POST | `{question, top_k (1–20), session_id, language}` → answer, references, retrieved chunks, helplines, complaint link |
| `/api/health` | GET | liveness + vector-DB status |
| `/api/feedback` | POST | `{vote, question}` → stores `{ts, vote, question_hash}` only |
| `/api/tts` | POST | server-side Urdu audio — **disabled by default** (`TTS_ENABLED=0`) to avoid API cost |

## Security & privacy

- API key is read **only from the environment**; it appears in no file, response or log.
- `/docs` and `/openapi.json` are disabled; every response carries `nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy` and a strict Content-Security-Policy.
- Per-IP rate limits protect the Gemini quota (30 questions/min, 12 audio requests/min).
- `top_k` is bounded server-side; blank/malformed input is rejected with 400/422, never 500.
- Feedback is anonymous by design: only a timestamp, a vote and a SHA-256 prefix of the question.
- The official complaint link opens in a new tab with `rel="noopener noreferrer"`.

## Test highlights

| Area | Result |
|---|---|
| Golden-set answer accuracy (EN + UR) | 100% — correct act & section cited, no hallucinations |
| Language routing | 100% correct EN/UR detection and response language |
| Retrieval hit@3 | 88% (missed case still answered correctly) |
| Latency | health 13–20 ms · query p50 ≈ 2.9 s, p95 ≈ 3.7 s |
| Concurrency | 5 parallel users, isolated sessions, correct follow-up resolution |
| Safety | urgent queries return 6 official helplines; normal queries return none |

## Deployment (Render)

The repo deploys as-is via `render.yaml` / `Procfile`:

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn Backend.server:app --host 0.0.0.0 --port $PORT`
- **Required env var:** `GEMINI_API_KEY`
- Optional: `QUERY_RATE_LIMIT`, `TTS_ENABLED`, `TTS_MODEL`, `TTS_VOICE`, `TTS_MAX_CHARS`,
  `TTS_RATE_LIMIT`, `TTS_CACHE_MAX`, `COMPLAINT_URL`

HTTPS on Render also enables microphone input on mobile browsers.

## Future scope

- **Urdu server-side voice output** — already implemented and gated behind `TTS_ENABLED`
  (parked to avoid recurring API cost).
- **Knowledge graph** over offence → punishment → bail → court relations for multi-hop queries.
- Case-law layer (judgments in addition to statutes).
- Streaming answers and a semantic cache for repeat questions.
- More Pakistani languages (Sindhi, Pashto, Balochi) and a lawyer-referral directory.

---

*CyberLaw Bot — legal information for every Pakistani, in their own language.*
