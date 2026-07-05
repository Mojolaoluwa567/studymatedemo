"""
RAG (retrieval-augmented generation) pipeline for long documents.

Problem this solves: quiz/study-aid generation used to truncate every
document to ~18k characters before sending it to Gemini. A short PDF fits
entirely; a 100-page textbook only ever got its first chapter quizzed.

Approach:
1. On upload, chunk the document into ~1000-token pieces (with overlap so
   concepts spanning a chunk boundary aren't lost).
2. Embed each chunk using Gemini's embedding model (free, no extra cost
   beyond the generation calls already being made).
3. At quiz/study-aid generation time, embed the "query" (a description of
   what's being generated - e.g. the difficulty tier + topic hints) and
   retrieve the most relevant chunks by cosine similarity, instead of
   blindly using the first N characters.

Chunking runs regardless of database backend. Embedding + retrieval only
activate for documents with chunks below EMBED_THRESHOLD_CHARS characters
generate nothing extra: short documents fit whole either way, so chunking
them adds latency for zero benefit - they still use the direct
truncate_for_prompt() path.
"""
import logging
import re

CHUNK_SIZE_CHARS = 3500       # ~1000 tokens, rough heuristic (4 chars/token)
CHUNK_OVERLAP_CHARS = 400     # keeps concepts spanning a boundary intact
EMBED_THRESHOLD_CHARS = 18000  # below this, chunking adds no value - skip it
TOP_K_CHUNKS = 8               # how many chunks to retrieve per generation
EMBEDDING_MODEL = "text-embedding-004"


def should_chunk(text_content):
    """Documents shorter than the old truncation limit get no benefit
    from chunking - they already fit whole. Only chunk genuinely long
    documents."""
    return len(text_content) > EMBED_THRESHOLD_CHARS


def chunk_text(text_content):
    """
    Splits text into overlapping chunks on paragraph boundaries where
    possible (falls back to a hard character split if a single paragraph
    exceeds the chunk size, which happens with badly-formatted PDFs that
    extract as one giant unbroken block).
    """
    paragraphs = re.split(r"\n\s*\n", text_content)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= CHUNK_SIZE_CHARS:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_SIZE_CHARS:
                # Single paragraph too large on its own - hard split it
                for i in range(0, len(para), CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS):
                    chunks.append(para[i:i + CHUNK_SIZE_CHARS])
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Add overlap between consecutive chunks so a concept split across a
    # boundary still appears intact in at least one chunk.
    overlapped = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            prev_tail = chunks[i - 1][-CHUNK_OVERLAP_CHARS:]
            chunk = f"{prev_tail}\n\n{chunk}"
        overlapped.append(chunk)

    return overlapped


def embed_texts(texts):
    """
    Calls Gemini's embedding model for a batch of texts in a single API
    call (the SDK accepts contents=list[str] directly). Returns a list
    of embedding vectors (list[float]) in the same order as the input.
    Raises on failure - caller decides whether to fall back gracefully.
    """
    from quiz_generator import get_client

    client = get_client()
    capped_texts = [t[:8000] for t in texts]  # embedding models have their own input cap
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=capped_texts,
    )
    return [e.values for e in result.embeddings]


def embed_document_chunks(document):
    """
    Chunks a document's text and stores embedded DocumentChunk rows.
    Called after upload for documents long enough to benefit (see
    should_chunk). Safe to call multiple times - clears existing chunks
    first so re-running doesn't duplicate.

    If embedding fails (Gemini error, rate limit, etc.), logs and leaves
    the document with no chunks - callers fall back to the old truncation
    behavior automatically since retrieve_relevant_chunks() returns an
    empty list when there are no chunks to search.
    """
    from models import db, DocumentChunk

    if not should_chunk(document.text_content):
        return

    # Clear any existing chunks (re-embedding case)
    DocumentChunk.query.filter_by(document_id=document.id).delete()

    chunks = chunk_text(document.text_content)
    if not chunks:
        return

    try:
        embeddings = embed_texts(chunks)
    except Exception as e:
        logging.error(f"Chunk embedding failed for document {document.id}: {e}")
        db.session.commit()  # commit the delete even if embedding failed
        return

    for i, (chunk_text_, embedding) in enumerate(zip(chunks, embeddings)):
        db.session.add(DocumentChunk(
            document_id=document.id,
            chunk_index=i,
            text=chunk_text_,
            embedding=embedding,
        ))
    db.session.commit()
    logging.info(f"Embedded {len(chunks)} chunks for document {document.id}")


def _cosine_similarity(a, b):
    """Plain-Python cosine similarity - no numpy dependency needed for
    the chunk counts involved here (dozens, not thousands)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_relevant_chunks(document, query_text, top_k=TOP_K_CHUNKS):
    """
    Returns the top_k most relevant chunk texts for the given query,
    joined into a single string ready to drop into a generation prompt.

    Returns None if the document has no chunks (either it was short
    enough not to need chunking, or embedding failed at upload time) -
    callers should fall back to truncate_for_prompt(document.text_content)
    in that case, preserving the old behavior for documents RAG doesn't
    apply to.
    """
    from models import DocumentChunk

    chunks = DocumentChunk.query.filter_by(document_id=document.id).all()
    chunks = [c for c in chunks if c.embedding]
    if not chunks:
        return None

    try:
        query_embedding = embed_texts([query_text])[0]
    except Exception as e:
        logging.error(f"Query embedding failed, falling back to truncation: {e}")
        return None

    scored = [
        (chunk, _cosine_similarity(query_embedding, chunk.embedding))
        for chunk in chunks
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    top_chunks = [chunk.text for chunk, _score in scored[:top_k]]

    return "\n\n---\n\n".join(top_chunks)


def get_prompt_text_for_document(document, query_hint):
    """
    The single entry point generation code should call instead of raw
    truncate_for_prompt(document.text_content) - decides between RAG
    retrieval (long documents with embedded chunks) and the original
    truncation behavior (short documents, or long ones where embedding
    failed at upload time) transparently.

    query_hint: a short string describing what's being generated (e.g.
    "Stage 2 Hard difficulty MCQ quiz covering the full document" or
    "study summary") - used as the retrieval query so chunk selection is
    at least loosely relevant to the generation task, rather than a fixed
    generic query for every call site.
    """
    from content_ingestion import truncate_for_prompt

    retrieved = retrieve_relevant_chunks(document, query_hint)
    if retrieved is not None:
        return retrieved

    return truncate_for_prompt(document.text_content)
