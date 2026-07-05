"""
AI study aids generated from a document's text: summary, key concepts, and
flashcards. Each is a single Gemini call returning structured JSON, cached
on the Document row by the caller (see app.py) so repeat visits don't
re-generate.
"""

import json
from quiz_generator import get_client, MODEL, _parse_json_array


def generate_summary(document_text):
    """Returns a plain string: a concise study summary of the material."""
    prompt = (
        "Write a concise study summary of the material below, in your own "
        "words. Cover the main topics and how they relate to each other. "
        "Aim for 150-300 words, organized into short paragraphs. Respond "
        "with ONLY the summary text - no headers, no markdown, no preamble."
        f"\n\n--- STUDY MATERIAL ---\n{document_text}"
    )

    response = get_client().models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def generate_key_concepts(document_text):
    """Returns a list of {term, explanation} dicts."""
    prompt = (
        "Identify the 6-10 most important concepts, terms, or ideas in the "
        "study material below that a student should know. For each, give "
        "the term/concept name and a 1-2 sentence plain-language "
        "explanation.\n\n"
        "Respond with ONLY a JSON array (no markdown, no commentary), where "
        'each element is {"term": "...", "explanation": "..."}.'
        f"\n\n--- STUDY MATERIAL ---\n{document_text}"
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        concepts = _parse_json_array(response.text)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Failed to parse key concepts response: {e}")

    return concepts


def generate_flashcards(document_text):
    """Returns a list of {front, back} dicts."""
    prompt = (
        "Create 10-15 flashcards from the study material below, suitable "
        "for active-recall practice. Each flashcard should have a 'front' "
        "(a question, term, or prompt) and a 'back' (the answer or "
        "explanation). Cover a spread of the material, not just one "
        "section.\n\n"
        "Respond with ONLY a JSON array (no markdown, no commentary), where "
        'each element is {"front": "...", "back": "..."}.'
        f"\n\n--- STUDY MATERIAL ---\n{document_text}"
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        cards = _parse_json_array(response.text)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Failed to parse flashcards response: {e}")

    return cards


def generate_explainer(document_text):
    """
    Generates a self-contained interactive HTML page that explains the
    material in a structured, visual way - collapsible sections, a
    glossary, worked examples where possible. Designed to be rendered in
    a sandboxed iframe (allow-scripts only) so the student can interact
    with it without it touching the app's own DOM or localStorage.

    Returns a complete HTML string. Critically:
    - No external scripts, stylesheets, or images (CDN links etc. would
      fail in the sandboxed iframe and break the experience)
    - No fetch/XHR calls (blocked by sandbox anyway, but we don't want
      the AI to try)
    - All CSS and JS inline in the single HTML document
    - Dark/light mode aware via prefers-color-scheme media query
    """
    prompt = (
        "Generate a complete, self-contained, interactive HTML page that "
        "explains the study material below in a structured, visually "
        "organized way - like a premium educational webpage, not a wall "
        "of plain text.\n\n"
        "REQUIREMENTS:\n"
        "1. A single HTML file with ALL CSS and JavaScript inline. "
        "   Do NOT reference any external files, CDNs, fonts, images, "
        "   or URLs of any kind - the page has no internet access.\n"
        "2. Include these sections (in order):\n"
        "   - A clear title and one-paragraph overview of what this "
        "     material is about\n"
        "   - 3-6 topic sections, each collapsible (click to expand), "
        "     covering the main concepts with structured explanations\n"
        "   - A 'Key Terms' glossary section with definitions\n"
        "   - A 'Quick Review' section with 3-5 short questions and "
        "     toggle-to-reveal answers\n"
        "3. Visual design:\n"
        "   - Use a clean, modern sans-serif font stack (system fonts only: "
        "     -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)\n"
        "   - Respect prefers-color-scheme: dark/light mode both look good\n"
        "   - Use accent colors, visual hierarchy, and spacing - not just "
        "     raw HTML structure\n"
        "   - Cards, panels, or sections with subtle borders/shadows\n"
        "4. All interactivity via vanilla JavaScript only (no libraries). "
        "   Toggle sections, reveal answers, smooth transitions.\n"
        "5. No fetch(), XHR, WebSocket, localStorage, sessionStorage, "
        "   cookies, or any external calls whatsoever.\n"
        "6. The page should feel like studying from a premium educational "
        "   platform, not a reformatted PDF.\n\n"
        "Respond with ONLY the complete HTML document, starting with "
        "<!DOCTYPE html>. No explanation, no markdown, no code fences.\n\n"
        f"--- STUDY MATERIAL ---\n{document_text}"
    )

    response = get_client().models.generate_content(model=MODEL, contents=prompt)
    html = response.text.strip()

    # Strip markdown code fences if the model added them despite instructions
    if html.startswith("```"):
        lines = html.split("\n")
        html = "\n".join(lines[1:])
        if html.rstrip().endswith("```"):
            html = html.rstrip()[:-3].rstrip()

    # Basic sanity check - if it doesn't look like HTML, raise so the
    # caller doesn't cache garbage
    if "<!DOCTYPE" not in html and "<html" not in html.lower():
        raise ValueError("Explainer generation returned invalid HTML")

    return html

