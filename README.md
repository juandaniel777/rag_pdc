# sugerir-rae — Prompt & endpoint reference

This document explains the prompt implementation and the `/api/sugerir-rae` POST endpoint in this project. It documents how retrieval is composed into the prompt, accepted request/response formats, environment variables, and quick examples for testing.

---

## Overview
- Endpoint: `POST /api/sugerir-rae`
- Purpose: accept a short **preliminary course description** and return a single course objective composed by a model using Retrieval‑Augmented Generation (RAG).
- Output: plain text (model's final objective). The server returns `Content-Type: text/plain; charset=utf-8` on success.

---

## Prompt template (exact)
The code inserts retrieved context fragments before sending the prompt to the model. The prompt used in `api/views.py` is:

```
You are an expert in university curriculum design.

INSTITUTIONAL CONTEXT:
{fragments retrieved from the vector database}

INSTRUCTOR INFORMATION:
Preliminary course description: {user_input}

INSTRUCTIONS: Write a course objective that:
- Is consistent with the institutional curriculum model.

- Is student-centered.

- Reflects the course's contribution to the graduate profile.

- Maintains conceptual clarity and disciplinary relevance.

- sugest always rae.

Return only the final text.
```

Notes:
- `{fragments retrieved from the vector database}` is replaced with the top‑k retrieved chunks (k=3).
- The handler returns **only the final text** (no extra markup).

---

## How retrieval works (RAG)
- Source document: `document/document.txt` (chunked by paragraphs / max 1000 chars).
- Embeddings: model `text-embedding-3-small` (constant `EMBED_MODEL`).
- Retrieval: top‑k cosine similarity (k = 3) against in‑memory `_DOCUMENT_EMBEDDINGS`.
- If embeddings or document are unavailable, the prompt receives `(no institutional context available)`.

---

## Request / Response
- Method: POST
- URL: `/api/sugerir-rae`
- Headers: `Content-Type: application/json`
- Accepted JSON fields (any of): `text`, `sugerencia`, `texto` — the handler picks the first present value.

Example request body:

```json
{ "text": "Finalidad del curso: ... (short course description)" }
```

Success response:
- HTTP 200
- Body: plain text (the course objective)

Error responses:
- 400 — invalid JSON or missing/invalid `text` field
- 405 — method not allowed (only POST supported)
- 500 — server error (e.g. `GROQ_API_KEY` not configured or model request failed)

---

## Environment / configuration
- Required env var: `GROQ_API_KEY` (or `grok_key` — `backend/settings.py` maps fallback). If not set, endpoint returns HTTP 500.
- Models configured in code:
  - Embedding model: `text-embedding-3-small`
  - Response model: `openai/gpt-oss-20b`

### Install dependencies from packages.txt
If you exported dependencies with `python -m pip freeze > packages.txt`, install them into your active Python environment with the commands below.

1. Activate the virtual environment for this project (examples):
   - PowerShell: `& .venv\Scripts\Activate.ps1`
   - CMD: `.\.venv\Scripts\activate.bat`
   - macOS / Linux: `source .venv/bin/activate`

2. Install packages from `packages.txt`:

```bash
python -m pip install -r packages.txt
```

This installs the exact package versions listed in `packages.txt`.

---

## Examples
Curl (local dev):

```bash
curl -X POST http://127.0.0.1:8000/api/sugerir-rae \
  -H "Content-Type: application/json" \
  -d '{"text":"Finalidad del curso: Introducir a estudiantes en POO — herencia y polimorfismo."}'
```

Fetch (frontend):

```js
fetch('/api/sugerir-rae', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Short course description here' })
})
.then(r => r.text())
.then(t => console.log('Objective:', t))
.catch(err => console.error(err));
```

---

## Debugging & logs
- The server prints the assembled `context_block` (see `print(f"Context block: {context_block}")`) — inspect dev server logs to see which fragments were retrieved.
- Common causes for failure:
  - Missing `GROQ_API_KEY` → 500
  - No `document/document.txt` or embedding failure → retrieval will be skipped and the prompt contains `(no institutional context available)`
  - Invalid request JSON or missing `text` → 400

---

## Security & production notes
- Do not allow `CORS_ALLOW_ALL_ORIGINS` in production. Use `CORS_ALLOWED_ORIGINS` and restrict access.
- Validate and rate‑limit incoming requests before forwarding to the model.
- Keep `GROQ_API_KEY` secret — use environment variables or a secrets manager.

---

## Quick improvements you can make to the prompt
- Add explicit output constraints (length, sentence count, or bullet format).
- Provide 1–2 examples (input → expected objective) to reduce variability.

---

If you want, I can: add example unit tests for `sugerir_rae`, show how to add stricter validation, or update the front-end `script.js` to call this endpoint.  