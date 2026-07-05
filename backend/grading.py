"""
Grading logic.

MCQ: deterministic comparison against the stored correct option key.
Theory: sent to Gemini along with the model answer / marking points for a
score (0..max marks) and short feedback.
"""

import json
import os
from dotenv import load_dotenv
from quiz_generator import get_client, MODEL, _parse_json_array

load_dotenv()


def grade_mcq(question, user_answer):
    """Returns (score_awarded, is_correct)."""
    is_correct = bool(
        user_answer and user_answer.strip().upper() == question.correct_answer.strip().upper()
    )
    return (question.marks if is_correct else 0), is_correct


def grade_theory_batch(theory_items):
    """
    theory_items: list of dicts with keys:
        question_text, model_answer, marks, user_answer

    Returns a list of dicts: {"score": float, "feedback": str}, same order.
    Falls back to a score of 0 with a generic note if grading fails.
    """
    if not theory_items:
        return []

    prompt_items = []
    for i, item in enumerate(theory_items):
        prompt_items.append(
            f"Question {i + 1} (max {item['marks']} marks):\n"
            f"{item['question_text']}\n\n"
            f"Marking points / model answer:\n{item['model_answer']}\n\n"
            f"Student's answer:\n{item['user_answer'] or '(no answer given)'}\n"
        )

    prompt = (
        "You are grading short-essay/theory exam answers. For each question "
        "below, award a score between 0 and the stated maximum marks based on "
        "how well the student's answer covers the marking points, and give "
        "brief (1-2 sentence) feedback explaining the score and what, if "
        "anything, was missed.\n\n"
        "Respond with ONLY a JSON array (no markdown, no commentary), where "
        "each element is {\"score\": <number>, \"feedback\": \"...\"}, in the "
        "same order as the questions below.\n\n"
        + "\n---\n".join(prompt_items)
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        results = _parse_json_array(response.text)
    except (json.JSONDecodeError, IndexError):
        results = [
            {"score": 0, "feedback": "Automatic grading failed for this answer."}
            for _ in theory_items
        ]

    # Clamp scores to valid range and ensure correct length.
    cleaned = []
    for item, result in zip(theory_items, results):
        score = float(result.get("score", 0))
        score = max(0, min(item["marks"], score))
        cleaned.append({"score": score, "feedback": result.get("feedback", "")})

    return cleaned


def explain_mistakes_batch(items):
    """
    items: list of dicts with keys:
        question_text, marks, score_awarded,
        type ("mcq" | "theory"),
        - for mcq: options, correct_answer, user_answer
        - for theory: model_answer, user_answer, feedback

    Returns a list of plain-language explanation strings, same order,
    covering: why the correct answer is right, why the student's answer
    was marked the way it was, and what to revise.
    """
    if not items:
        return []

    prompt_items = []
    for i, item in enumerate(items):
        if item["type"] == "mcq":
            options_text = "\n".join(
                f"  {k}: {v}" for k, v in (item.get("options") or {}).items()
            )
            prompt_items.append(
                f"Question {i + 1} ({item['marks']} marks, scored "
                f"{item['score_awarded']}):\n{item['question_text']}\n"
                f"Options:\n{options_text}\n"
                f"Correct answer: {item['correct_answer']}\n"
                f"Student's answer: {item.get('user_answer') or '(no answer given)'}\n"
            )
        else:
            prompt_items.append(
                f"Question {i + 1} ({item['marks']} marks, scored "
                f"{item['score_awarded']}):\n{item['question_text']}\n"
                f"Marking points / model answer: {item['model_answer']}\n"
                f"Student's answer: {item.get('user_answer') or '(no answer given)'}\n"
                f"Grader feedback: {item.get('feedback') or '(none)'}\n"
            )

    prompt = (
        "A student got the following exam questions wrong or partially "
        "wrong. For EACH question, write a short (2-4 sentence) explanation "
        "in plain language that: (1) explains why the correct answer is "
        "right, (2) explains the likely misunderstanding behind the "
        "student's answer, and (3) suggests what specific concept they "
        "should revise. Be encouraging, not harsh.\n\n"
        "Respond with ONLY a JSON array of strings (no markdown, no "
        "commentary), one explanation per question, in the same order as "
        "the questions below.\n\n"
        + "\n---\n".join(prompt_items)
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        results = _parse_json_array(response.text)
    except (json.JSONDecodeError, IndexError):
        results = ["Explanation unavailable right now." for _ in items]

    # Ensure correct length.
    if len(results) != len(items):
        results = (results + [""] * len(items))[: len(items)]
        results = [r or "Explanation unavailable right now." for r in results]

    return [str(r) for r in results]
