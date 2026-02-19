import json
import os
import math
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt

# OpenAI / GROQ client (uses env var GROQ_API_KEY)
from openai import OpenAI

# prefer GROQ_API_KEY (backend/settings.py maps `grok_key` → `GROQ_API_KEY` if present)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY') or os.environ.get('grok_key')
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

EMBED_MODEL = "text-embedding-3-small"
RESPONSE_MODEL = "openai/gpt-oss-20b"

# In-memory vector store for document.txt (built lazily)
_DOCUMENT_EMBEDDINGS = []  # list of {'text': chunk, 'embedding': [...]}


def _chunk_text(text, max_chars=1000):
    """Simple chunker: split by paragraphs then slice long paragraphs."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for p in paras:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            for i in range(0, len(p), max_chars):
                chunks.append(p[i:i + max_chars])
    if not chunks and text.strip():
        for i in range(0, len(text), max_chars):
            chunks.append(text[i:i + max_chars])
    return chunks


def _cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norma = math.sqrt(sum(x * x for x in a))
    normb = math.sqrt(sum(y * y for y in b))
    if norma == 0 or normb == 0:
        return 0.0
    return dot / (norma * normb)


def _ensure_vector_store():
    """Load and embed `document.txt` into memory (no-op if already loaded)."""
    global _DOCUMENT_EMBEDDINGS
    if _DOCUMENT_EMBEDDINGS:
        return

    # load the institutional document from `document/document.txt` (single-source)
    doc_path = os.path.join(settings.BASE_DIR, 'document', 'document.txt')
    if not os.path.exists(doc_path) or client is None:
        return

    with open(doc_path, 'r', encoding='utf-8') as fh:
        doc_text = fh.read()

    chunks = _chunk_text(doc_text, max_chars=1000)
    if not chunks:
        return

    try:
        resp = client.embeddings.create(input=chunks, model=EMBED_MODEL)
        embeddings = [d['embedding'] for d in resp.data]
        _DOCUMENT_EMBEDDINGS = [{'text': chunks[i], 'embedding': embeddings[i]} for i in range(len(chunks))]
    except Exception:
        # silently skip vector store on failure; retrieval will be disabled
        _DOCUMENT_EMBEDDINGS = []


def _get_top_k_contexts(query, k=3):
    """Return top-k text chunks from `document.txt` most similar to query."""
    _ensure_vector_store()
    if not _DOCUMENT_EMBEDDINGS or client is None:
        return []

    try:
        q_emb_resp = client.embeddings.create(input=[query], model=EMBED_MODEL)
        q_emb = q_emb_resp.data[0]['embedding']
    except Exception:
        return []

    scored = []
    for item in _DOCUMENT_EMBEDDINGS:
        score = _cosine_sim(q_emb, item['embedding'])
        scored.append((score, item['text']))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:k]]


@csrf_exempt
def sugerir_rae(request):
    """Agent endpoint — accepts JSON {"text": "..."}, performs RAG, returns plain text.

    Prompt template (exactly):

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

    Return only the final text.
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON')

    user_text = payload.get('text') or payload.get('sugerencia') or payload.get('texto')
    if not user_text or not isinstance(user_text, str):
        return HttpResponseBadRequest('Missing or invalid "text" field')

    if client is None:
        return HttpResponseServerError('GROQ_API_KEY not configured in environment')

    # retrieval
    contexts = _get_top_k_contexts(user_text, k=3)
    context_block = "\n\n".join(contexts) if contexts else "(no institutional context available)"
    print(f"Context block: {context_block}")
    prompt = (
        "You are an expert in university curriculum design.\n\n"
        f"INSTITUTIONAL CONTEXT:\n{context_block}\n\n"
        f"INSTRUCTOR INFORMATION:\nPreliminary course description: {user_text}\n\n"
        "INSTRUCTIONS: Write a course objective that:\n"
        "- Is consistent with the institutional curriculum model.\n\n"
        "- Is student-centered.\n\n"
        "- Reflects the course's contribution to the graduate profile.\n\n"
        "- Maintains conceptual clarity and disciplinary relevance.\n\n"
        
        "- sugest always rae.\n\n"
        "Return only the final text."
    )

    try:
        resp = client.responses.create(input=prompt, model=RESPONSE_MODEL)
        output = getattr(resp, 'output_text', None) or (resp.output[0].get('content', [{}])[0].get('text') if getattr(resp, 'output', None) else '')
    except Exception as exc:
        return HttpResponseServerError(f'Model request failed: {exc}')

    return HttpResponse(output.strip(), content_type='text/plain; charset=utf-8', status=200)
