"""
Quiz generation via the Gemini API (free tier - no credit card required).

3-stage exam structure:

STAGE 1 — EASY (practice/entry layer, MCQ only)
  Format A: 40 questions × 1 mark = 40 marks, 30 min
  Format B: 20 questions × 2 marks = 40 marks, 25 min
  Tests basic recall, definitions, simple concept checks.

STAGE 2 — HARD (main objective exam, mostly MCQ + 1 short theory question)
  Format A: 60 MCQ × 1 mark + 1 theory × 5 marks = 65 marks, 50 min
  Format B: 30 MCQ × 2 marks + 1 theory × 8 marks = 68 marks, 40 min
  Twisted MCQs, NOT/EXCEPT phrasing, scenario-based, compare A vs B.
  Tests deeper understanding and ability to avoid confusion between
  similar-looking answers. The single theory question is lighter-weight
  than Difficult's essay questions - a quick written check, not a full
  multi-paragraph response.

STAGE 3 — DIFFICULT (final exam simulation, MCQ + theory)
  Format A: 60 MCQ × 1 mark + 10 theory × 4 marks = 100 marks, 75 min
  Format B: 30 MCQ × 2 marks + 5 theory × 8 marks = 100 marks, 90 min
  Objective side = 60 marks (60%), theory side = 40 marks (40%).
  Theory questions are ONLY in this tier - mimics a real final exam.

QUESTION PATTERN TRAINER (formerly "Lecturer Style")
  Same format options as Hard (60/30 objective questions, 60 marks).
  Questions are about the student's course material but written to
  match the phrasing, twist style, and format preferences of a
  specific lecturer derived from uploaded past questions.
  No theory questions - the point is to master the objective pattern.
"""

import json
import os
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

_client = None


def get_client():
    """Lazily create the Gemini client so the app can still start (and
    serve auth/document endpoints) even if GEMINI_API_KEY isn't set yet."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env "
                "(get a free key at https://aistudio.google.com/app/apikey)."
            )
        _client = genai.Client(api_key=api_key)
    return _client

FORMATTING_RULES = (
    "TEXT FORMATTING RULES (apply to every question, option, and answer):\n"
    "- Never use markdown syntax inside question/option/answer text - no "
    "  backticks, no asterisks for bold/italic, no markdown headers. This "
    "  text is rendered as plain text, so markdown artifacts show up as "
    "  literal stray characters to the student.\n"
    "- For code snippets referenced in a question, write them as plain "
    "  inline text (e.g. for i in range(10)) without any backticks or "
    "  code-fence wrapping.\n"
    "- For math and logic, use proper Unicode symbols instead of writing "
    "  them out or using asterisks: × for multiplication, ÷ for division, "
    "  ≤ ≥ ≠ ± √ π for their respective operators, → for implication/"
    "  arrows, ² ³ for exponents where applicable. Do not use * for "
    "  multiplication or ^ for exponents in question text.\n"
    "- Write questions in clear, standard, grammatically correct English - "
    "  no run-on phrasing, no ambiguous pronoun references.\n"
)


# ---------------------------------------------------------------------------
# Stage 1 — Easy (MCQ only, two format options)
# ---------------------------------------------------------------------------
EASY_MODES = {
    40: {"num_questions": 40, "marks_per_question": 1, "time_limit_minutes": 30},
    20: {"num_questions": 20, "marks_per_question": 2, "time_limit_minutes": 25},
}

# ---------------------------------------------------------------------------
# Stage 2 — Hard (MCQ only, two format options, no theory)
# Hard is pure objective - theory lives entirely in Difficult.
# ---------------------------------------------------------------------------
HARD_MODES = {
    60: {
        "mcq_count": 60,
        "mcq_marks": 1,
        "theory_count": 1,
        "theory_marks": 5,
        "time_limit_minutes": 50,
    },
    30: {
        "mcq_count": 30,
        "mcq_marks": 2,
        "theory_count": 1,
        "theory_marks": 8,
        "time_limit_minutes": 40,
    },
}

# ---------------------------------------------------------------------------
# Stage 3 — Difficult (MCQ + theory, two format options, 100 marks total)
# Objective = 60 marks (60%), theory = 40 marks (40%)
# ---------------------------------------------------------------------------
DIFFICULT_MODES = {
    60: {
        "mcq_count": 60,
        "mcq_marks": 1,
        "theory_count": 10,
        "theory_marks": 4,
        "time_limit_minutes": 75,
    },
    30: {
        "mcq_count": 30,
        "mcq_marks": 2,
        "theory_count": 5,
        "theory_marks": 8,
        "time_limit_minutes": 90,
    },
}

# ---------------------------------------------------------------------------
# Question Pattern Trainer (formerly Lecturer Style)
# Same format options as Hard - pure objective, learned style.
# ---------------------------------------------------------------------------
PATTERN_TRAINER_MODES = {
    60: {
        "mcq_count": 60,
        "mcq_marks": 1,
        "time_limit_minutes": 45,
    },
    30: {
        "mcq_count": 30,
        "mcq_marks": 2,
        "time_limit_minutes": 35,
    },
}


def get_quiz_plan(difficulty, format_mode=60):
    """
    Returns the full quiz plan for a given difficulty + format choice.
    format_mode: 60 = more questions, 1 mark each; 30 = fewer, higher marks.
    All difficulties accept both format options.
    """
    if difficulty == "easy":
        cfg = EASY_MODES.get(format_mode, EASY_MODES[40])
        return {
            "difficulty": "easy",
            "mcq_count": cfg["num_questions"],
            "mcq_marks": cfg["marks_per_question"],
            "theory_count": 0,
            "theory_marks": 0,
            "time_limit_minutes": cfg["time_limit_minutes"],
            "total_marks": cfg["num_questions"] * cfg["marks_per_question"],
            "num_questions": cfg["num_questions"],
            "format_mode": format_mode,
        }

    if difficulty == "hard":
        cfg = HARD_MODES.get(format_mode, HARD_MODES[60])
        obj_marks = cfg["mcq_count"] * cfg["mcq_marks"]
        theory_marks = cfg["theory_count"] * cfg["theory_marks"]
        return {
            "difficulty": "hard",
            "mcq_count": cfg["mcq_count"],
            "mcq_marks": cfg["mcq_marks"],
            "theory_count": cfg["theory_count"],
            "theory_marks": cfg["theory_marks"],
            "time_limit_minutes": cfg["time_limit_minutes"],
            "total_marks": obj_marks + theory_marks,
            "num_questions": cfg["mcq_count"] + cfg["theory_count"],
            "format_mode": format_mode,
        }

    if difficulty == "difficult":
        cfg = DIFFICULT_MODES.get(format_mode, DIFFICULT_MODES[60])
        obj_marks = cfg["mcq_count"] * cfg["mcq_marks"]
        theory_marks = cfg["theory_count"] * cfg["theory_marks"]
        return {
            "difficulty": "difficult",
            "mcq_count": cfg["mcq_count"],
            "mcq_marks": cfg["mcq_marks"],
            "theory_count": cfg["theory_count"],
            "theory_marks": cfg["theory_marks"],
            "time_limit_minutes": cfg["time_limit_minutes"],
            "total_marks": obj_marks + theory_marks,
            "num_questions": cfg["mcq_count"] + cfg["theory_count"],
            "format_mode": format_mode,
        }

    if difficulty == "lecturer_style":
        cfg = PATTERN_TRAINER_MODES.get(format_mode, PATTERN_TRAINER_MODES[60])
        total = cfg["mcq_count"] * cfg["mcq_marks"]
        return {
            "difficulty": "lecturer_style",
            "mcq_count": cfg["mcq_count"],
            "mcq_marks": cfg["mcq_marks"],
            "theory_count": 0,
            "theory_marks": 0,
            "time_limit_minutes": cfg["time_limit_minutes"],
            "total_marks": total,
            "num_questions": cfg["mcq_count"],
            "format_mode": format_mode,
        }

    # Fallback - shouldn't be reached in normal operation
    return get_quiz_plan("easy", format_mode)


def _build_lecturer_style_prompt(content_text, style_sample_text, plan):
    """
    Two-document prompt for the Question Pattern Trainer mode.
    Section A = the actual course material to quiz on.
    Section B = the lecturer's past questions - a pattern reference only.

    The AI should learn HOW the lecturer asks questions (their phrasing,
    twist techniques, favourite formats, objective/theory balance) from
    Section B, then generate NEW questions ABOUT Section A content in that
    same pattern. Section B is never a source of facts or answers.

    This mode generates pure MCQ only - no theory - because the goal is
    mastering the objective question pattern, not theory writing.
    """
    style = (
        f"Generate exactly {plan['mcq_count']} multiple-choice questions "
        "based STRICTLY on the course material in Section A below.\n\n"
        "Section B contains past questions from a specific lecturer. Study "
        "Section B carefully to learn:\n"
        "1. HOW this lecturer twists questions (unusual angles, EXCEPT/NOT "
        "   phrasing, mixing related topics, confusingly similar options)\n"
        "2. Their favourite question formats and sentence structures\n"
        "3. How they word distractors to catch students who haven't studied\n"
        "4. Their overall difficulty and style signature\n\n"
        "Then generate new questions ABOUT the content in Section A, written "
        "in that exact same style and pattern. The content, facts, and correct "
        "answers MUST come from Section A only. Section B tells you HOW to "
        "ask — Section A tells you WHAT to ask about.\n\n"
        "Generate MCQ only — no theory questions in this mode."
    )

    schema = (
        "Respond with ONLY a JSON array (no markdown, no commentary, no code "
        "fences). Each element must be an object with these exact fields:\n"
        '- "type": "mcq"\n'
        '- "question": the question text\n'
        '- "options": an object {"A": "...", "B": "...", "C": "...", "D": "..."}\n'
        '- "correct_answer": the correct option key (e.g. "B")\n'
        f'- "marks": {plan["mcq_marks"]}\n'
        '- "topic": a short 2-4 word label for the specific concept this '
        'question tests (e.g. "CPU Scheduling", "Deadlock Conditions") - '
        "used to track which topics a student is strong/weak on\n\n"
        f"{FORMATTING_RULES}"
    )

    return (
        f"{style}\n\n{schema}\n\n"
        f"--- SECTION A: COURSE MATERIAL (quiz this) ---\n{content_text}\n\n"
        f"--- SECTION B: PAST QUESTIONS (pattern reference only - "
        f"do not quiz on this) ---\n{style_sample_text}"
    )


def _build_prompt(document_text, plan):
    difficulty = plan["difficulty"]
    mcq_count = plan["mcq_count"]
    theory_count = plan.get("theory_count", 0)
    mcq_marks = plan["mcq_marks"]
    theory_marks = plan.get("theory_marks", 0)

    if difficulty == "easy":
        style = (
            f"Generate exactly {mcq_count} multiple-choice questions based "
            "strictly on the study material below.\n\n"
            "This is Stage 1 — the entry/practice level. Questions should test "
            "basic recall and understanding: definitions, key terms, "
            "straightforward facts, and simple one-step concept checks directly "
            "from the material. No trick wording, no ambiguous options. A student "
            "who read the material carefully should get these right."
        )

    elif difficulty == "hard":
        style = (
            f"Generate exactly {mcq_count} multiple-choice questions AND "
            f"{theory_count} short theory question(s) based on the study "
            "material below.\n\n"
            "This is Stage 2 — the main objective exam layer. The MCQs should "
            "be significantly harder than simple recall:\n"
            "- Use 'which of the following is NOT...' or 'EXCEPT' phrasing\n"
            "- Create options that look almost identical so only someone who "
            "  truly understands the material can pick the right one\n"
            "- Ask application questions: give a scenario from the material and "
            "  ask what concept applies, or what the correct next step is\n"
            "- Compare two related concepts from the material in a single question\n"
            "- Use the kind of twists a university lecturer would use to catch "
            "  students who only skimmed the material\n\n"
            "Distractors must be genuinely plausible — not obviously wrong — so "
            "that only precise understanding eliminates them.\n\n"
            "FOR THE THEORY QUESTION(S):\n"
            "Keep this lighter than a full essay prompt - a focused 'Explain...' "
            "or 'Briefly discuss...' question that can be answered in a short "
            "paragraph, testing understanding of one specific concept from the "
            "material. Provide a 'model_answer' field with the key points a "
            "correct answer should cover, for grading reference."
        )

    else:  # difficult
        style = (
            f"Generate exactly {mcq_count} multiple-choice questions AND "
            f"{theory_count} essay-style questions based on the study material below.\n\n"
            "This is Stage 3 — the final exam simulation. It combines objective "
            f"questions ({mcq_count} MCQ = {mcq_count * mcq_marks} marks) and "
            f"essay questions ({theory_count} essay = "
            f"{theory_count * theory_marks} marks), totalling "
            f"{mcq_count * mcq_marks + theory_count * theory_marks} marks.\n\n"
            "FOR THE MCQs:\n"
            "Use wordplay, precise terminology, and application-style questions. "
            "Every scenario must come directly from the study material — do not "
            "invent unrelated fictional settings. Distractors should be plausible "
            "to someone with surface-level knowledge, requiring precise "
            "understanding to eliminate.\n\n"
            "FOR THE ESSAY QUESTIONS:\n"
            "These require genuine essay-style responses, not short answers. "
            "Write them as 'Discuss...', 'Compare and contrast...', 'Critically "
            "examine...', or 'Evaluate...' prompts that require synthesizing two "
            "or more related concepts from the material into a multi-paragraph "
            "answer — not just a definition. This is the written section of a "
            "final exam, so questions should demand the depth a lecturer would "
            "expect there. Provide a 'model_answer' field with the key marking "
            "points a strong essay answer must cover, for grading reference."
        )

    schema = (
        "Respond with ONLY a JSON array (no markdown, no commentary, no code "
        "fences). Each element must be an object with these exact fields:\n"
        '- "type": "mcq" or "theory"\n'
        '- "question": the question text\n'
        '- "options": for mcq only — an object {"A": "...", "B": "...", '
        '"C": "...", "D": "..."}\n'
        '- "correct_answer": for mcq, the correct option key (e.g. "B"); '
        'for theory, the model answer / marking points as a string\n'
        f'- "marks": {mcq_marks} for mcq'
        + (f", {theory_marks} for theory" if theory_count > 0 else "")
        + '\n- "topic": a short 2-4 word label for the specific concept this '
        'question tests (e.g. "CPU Scheduling", "Deadlock Conditions") - '
        "used to track which topics a student is strong/weak on\n\n"
        + FORMATTING_RULES
    )

    return f"{style}\n\n{schema}\n\n--- STUDY MATERIAL ---\n{document_text}"


def _parse_json_array(raw_text):
    text = raw_text.strip()
    # Strip markdown code fences if the model added them anyway.
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _normalize_questions(questions, plan):
    """
    Enforce the marking scheme server-side, regardless of what the LLM
    actually returned. This guarantees:
      - no more than plan['mcq_count'] MCQs and plan['theory_count'] theory
        questions are kept (extras are dropped)
      - every question's marks are forced to the configured value for its
        type, so per-question and total marks can never be inflated
      - plan['total_marks'] / plan['num_questions'] are recalculated to
        reflect what was ACTUALLY generated (in case the LLM returned
        fewer questions than requested), so the quiz total never exceeds
        the configured cap (e.g. 60 for Easy).
    """
    mcq = [q for q in questions if q.get("type") == "mcq"][: plan["mcq_count"]]
    theory = [q for q in questions if q.get("type") == "theory"][
        : plan["theory_count"]
    ]

    for q in mcq:
        q["marks"] = plan["mcq_marks"]
    for q in theory:
        q["marks"] = plan["theory_marks"]

    normalized = mcq + theory

    plan["num_questions"] = len(normalized)
    plan["total_marks"] = (
        len(mcq) * plan["mcq_marks"] + len(theory) * plan["theory_marks"]
    )

    return normalized


# ---------------------------------------------------------------------------
# Grounding check
# ---------------------------------------------------------------------------
#
# Cheap, no-AI-call defense against the model inventing content that isn't
# actually in the source document: extract the meaningful keywords from a
# generated question (+ its correct answer) and check what fraction of
# them actually appear in the source text. A genuinely grounded question -
# even reworded - will still share specific subject-matter terms with the
# source (names, technical terms, numbers); a fabricated one usually won't.
#
# This is deliberately a heuristic, not semantic verification - it will
# miss subtly-wrong claims made entirely out of words that DO appear in
# the text. A stronger (AI-call-based) verification pass is a documented
# future upgrade once a free-quota budget allows it; see README.

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "of", "in", "on", "at", "to", "for",
    "and", "or", "but", "not", "no", "which", "what", "who", "whom",
    "with", "as", "by", "from", "it", "its", "their", "his", "her",
    "do", "does", "did", "can", "could", "will", "would", "should",
    "true", "false", "all", "none", "following", "above", "below",
    "except", "one", "two", "three", "four", "questions", "question",
}

GROUNDING_MIN_OVERLAP = 0.3  # fraction of keywords that must appear in source


def _extract_keywords(text):
    """Lowercased alphanumeric tokens, length > 2, with stopwords removed."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _is_grounded(question, source_text_lower):
    """
    Returns True if enough of the question's (+ correct answer's) keywords
    appear in the source document text to consider it grounded.
    """
    pieces = [question.get("question", "")]

    if question.get("type") == "mcq":
        correct_key = str(question.get("correct_answer", ""))
        options = question.get("options") or {}
        # Include the TEXT of the correct option, not just its letter key,
        # since that's where the actual factual claim lives.
        if correct_key in options:
            pieces.append(options[correct_key])
    else:
        pieces.append(str(question.get("correct_answer", "")))

    keywords = _extract_keywords(" ".join(pieces))
    if not keywords:
        return True  # nothing meaningful to check - don't reject on a technicality

    matched = sum(1 for kw in keywords if kw in source_text_lower)
    overlap = matched / len(keywords)

    return overlap >= GROUNDING_MIN_OVERLAP


def _filter_grounded(questions, source_text):
    """
    Drops any question that fails the grounding heuristic. Returns the
    filtered list - callers are responsible for recalculating
    total_marks/num_questions afterward (same pattern as
    _normalize_questions), since this can change how many questions
    survive.
    """
    source_lower = source_text.lower()
    return [q for q in questions if _is_grounded(q, source_lower)]


def generate_quiz_questions(document_text, difficulty, format_mode=60):
    """
    Calls Gemini to generate quiz questions and returns
    (plan, questions_list) where questions_list is a list of dicts:
        {type, question, options, correct_answer, marks}

    format_mode: 60 = more questions at 1 mark each, 30 = fewer at higher marks.
    All three difficulty tiers (easy/hard/difficult) accept both format options.
    """
    plan = get_quiz_plan(difficulty, format_mode)
    prompt = _build_prompt(document_text, plan)

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    raw_text = response.text

    try:
        questions = _parse_json_array(raw_text)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Failed to parse quiz response as JSON: {e}")

    questions = _filter_grounded(questions, document_text)
    questions = _normalize_questions(questions, plan)

    if not questions:
        raise ValueError(
            "Quiz generation returned no usable questions grounded in "
            "your document. Try again, or use a longer/more detailed "
            "document."
        )

    return plan, questions


def generate_lecturer_style_quiz_questions(content_text, style_sample_text, format_mode=60):
    """
    Question Pattern Trainer: generates pure MCQ questions from content_text,
    written to match the question style/pattern found in style_sample_text
    (a lecturer's past questions). Returns (plan, questions_list).

    format_mode: 60 = 60 MCQ × 1 mark; 30 = 30 MCQ × 2 marks.
    Grounding check runs against content_text ONLY.
    """
    plan = get_quiz_plan("lecturer_style", format_mode)
    prompt = _build_lecturer_style_prompt(content_text, style_sample_text, plan)

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    raw_text = response.text

    try:
        questions = _parse_json_array(raw_text)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Failed to parse quiz response as JSON: {e}")

    questions = _filter_grounded(questions, content_text)
    questions = _normalize_questions(questions, plan)

    if not questions:
        raise ValueError(
            "Quiz generation returned no usable questions grounded in "
            "your content document. Try again, or use a longer/more "
            "detailed content document."
        )

    return plan, questions


def _build_weak_spots_prompt(document_text, weak_topics, plan):
    """
    Generates a focused practice quiz that concentrates on specific topics
    the student has historically scored low on, rather than sampling the
    whole document evenly like a normal quiz would.
    """
    topics_list = ", ".join(weak_topics)
    style = (
        f"Generate exactly {plan['mcq_count']} multiple-choice questions "
        "based strictly on the study material below.\n\n"
        f"This is a FOCUSED REVIEW quiz targeting the student's weak areas. "
        f"Concentrate your questions specifically on these topics: "
        f"{topics_list}. Do not spread questions evenly across the whole "
        "document - if the material covers other topics not in this list, "
        "skip them. Every question should relate to one of the listed "
        "weak topics.\n\n"
        "Write questions at a moderate difficulty - clear and direct "
        "enough to build confidence, but substantive enough to actually "
        "test understanding, not just recognition."
    )

    schema = (
        "Respond with ONLY a JSON array (no markdown, no commentary, no code "
        "fences). Each element must be an object with these exact fields:\n"
        '- "type": "mcq"\n'
        '- "question": the question text\n'
        '- "options": an object {"A": "...", "B": "...", "C": "...", "D": "..."}\n'
        '- "correct_answer": the correct option key (e.g. "B")\n'
        f'- "marks": {plan["mcq_marks"]}\n'
        f'- "topic": which of these topics this question targets: {topics_list}\n\n'
        f"{FORMATTING_RULES}"
    )

    return f"{style}\n\n{schema}\n\n--- STUDY MATERIAL ---\n{document_text}"


WEAK_SPOTS_CONFIG = {"mcq_count": 10, "mcq_marks": 2, "time_limit_minutes": 20}


def generate_weak_spots_quiz(document_text, weak_topics):
    """
    Generates a short, focused MCQ-only practice quiz on the student's
    weakest topics for this document. Returns (plan, questions_list).
    """
    cfg = WEAK_SPOTS_CONFIG
    plan = {
        "difficulty": "weak_spots",
        "mcq_count": cfg["mcq_count"],
        "mcq_marks": cfg["mcq_marks"],
        "theory_count": 0,
        "theory_marks": 0,
        "time_limit_minutes": cfg["time_limit_minutes"],
        "total_marks": cfg["mcq_count"] * cfg["mcq_marks"],
        "num_questions": cfg["mcq_count"],
        "format_mode": None,
    }
    prompt = _build_weak_spots_prompt(document_text, weak_topics, plan)

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    raw_text = response.text

    try:
        questions = _parse_json_array(raw_text)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Failed to parse quiz response as JSON: {e}")

    questions = _filter_grounded(questions, document_text)
    questions = _normalize_questions(questions, plan)

    if not questions:
        raise ValueError(
            "Weak-spots quiz generation returned no usable questions. "
            "Try again, or take a few more quizzes first to build up "
            "topic data."
        )

    return plan, questions


def transcribe_audio(audio_bytes, mime_type):
    """
    Transcribes an audio clip via Gemini, which accepts audio directly as
    input (no separate speech-to-text library needed). Used for both
    uploaded audio files and the YouTube no-captions fallback in
    content_ingestion.py - kept here, alongside the rest of the Gemini
    calls, and passed into those functions as a plain callable so
    content_ingestion.py has no direct dependency on the Gemini SDK.

    Returns the transcript as plain text.
    """
    from google.genai import types

    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    prompt = (
        "Transcribe this audio in full. Return ONLY the spoken words as "
        "plain text - no timestamps, no speaker labels, no commentary, no "
        "markdown formatting."
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=[prompt, audio_part],
    )

    return response.text