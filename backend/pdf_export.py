"""
PDF export for StudyMate - results cards and study guides.

Primary path: WeasyPrint (renders styled HTML/CSS to PDF - much better
visual quality than raw ReportLab flowables, and lets us reuse styling
that matches the app's own look).

Fallback path: ReportLab (pdf_export_reportlab.py) - used automatically
if WeasyPrint raises an error, which happens on hosts missing the system
libraries WeasyPrint depends on (Pango, Cairo, GDK-Pixbuf). Render's
default Python runtime doesn't include these unless explicitly installed,
so this fallback is not theoretical - keep it working, don't remove it.
"""
import io
import logging
from datetime import datetime
from html import escape

# WeasyPrint and fontTools log extensively at INFO level by default (every
# font subsetting step, every rendering stage) - fine for debugging, way
# too noisy for production logs on every single PDF export.
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)

ACCENT = "#6366F1"
CORRECT = "#22c55e"
INCORRECT = "#ef4444"
MUTED = "#94a3b8"
INK = "#1e293b"
BORDER = "#e2e8f0"

BASE_CSS = f"""
@page {{
    size: A4;
    margin: 2cm;
}}
* {{ box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: {INK};
    font-size: 10pt;
    line-height: 1.5;
}}
.brand {{
    font-family: monospace;
    font-size: 8pt;
    color: {ACCENT};
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 4px;
}}
h1 {{
    font-size: 20pt;
    color: {ACCENT};
    margin: 0 0 4px 0;
}}
.sub {{
    font-size: 9pt;
    color: {MUTED};
    margin-bottom: 16px;
}}
hr {{
    border: none;
    border-top: 1px solid {BORDER};
    margin: 12px 0 20px 0;
}}
h2 {{
    font-size: 13pt;
    margin: 20px 0 10px 0;
    border-bottom: 2px solid {ACCENT};
    padding-bottom: 4px;
}}
.score-box {{
    display: flex;
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 20px;
}}
.score-box > div {{
    flex: 1;
    text-align: center;
    padding: 16px 8px;
    background: #f8fafc;
}}
.score-box > div:first-child {{
    background: {ACCENT};
    color: white;
}}
.score-box .big {{ font-size: 22pt; font-weight: 700; }}
.score-box .label {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }}
.question {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 10px;
    page-break-inside: avoid;
}}
.question .topic {{
    font-size: 7.5pt;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}}
.question .qtext {{
    font-weight: 600;
    margin-bottom: 6px;
}}
.question .qnum {{
    font-family: monospace;
    color: {ACCENT};
    margin-right: 4px;
}}
.badge {{
    font-family: monospace;
    font-size: 8pt;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid;
    float: right;
}}
.badge.correct {{ color: {CORRECT}; border-color: {CORRECT}; }}
.badge.incorrect {{ color: {INCORRECT}; border-color: {INCORRECT}; }}
.badge.partial {{ color: {ACCENT}; border-color: {ACCENT}; }}
.feedback {{
    font-size: 8.5pt;
    color: {MUTED};
    font-style: italic;
    margin-top: 6px;
    padding-left: 8px;
    border-left: 2px solid {BORDER};
}}
.summary-text {{ line-height: 1.7; }}
.concept {{
    margin-bottom: 10px;
    padding-left: 4px;
}}
.concept .term {{ font-weight: 700; }}
.card {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    page-break-inside: avoid;
}}
.card .q {{ font-weight: 600; margin-bottom: 4px; }}
.card .a {{ color: #475569; }}
"""


def generate_results_pdf(attempt, quiz, breakdown, student_username):
    """Generates a printable results/report card PDF. Returns bytes."""
    try:
        return _generate_results_pdf_weasyprint(attempt, quiz, breakdown, student_username)
    except Exception as e:
        logging.warning(f"WeasyPrint results PDF failed, falling back to ReportLab: {e}")
        from pdf_export_reportlab import generate_results_pdf_reportlab
        return generate_results_pdf_reportlab(attempt, quiz, breakdown, student_username)


def generate_study_guide_pdf(document, summary, key_concepts, flashcards):
    """Generates a printable study guide PDF. Returns bytes."""
    try:
        return _generate_study_guide_pdf_weasyprint(document, summary, key_concepts, flashcards)
    except Exception as e:
        logging.warning(f"WeasyPrint study guide PDF failed, falling back to ReportLab: {e}")
        from pdf_export_reportlab import generate_study_guide_pdf_reportlab
        return generate_study_guide_pdf_reportlab(document, summary, key_concepts, flashcards)


def _generate_results_pdf_weasyprint(attempt, quiz, breakdown, student_username):
    from weasyprint import HTML, CSS

    percentage = attempt.percentage or 0
    grade = (
        "A" if percentage >= 70 else
        "B" if percentage >= 60 else
        "C" if percentage >= 50 else
        "D" if percentage >= 40 else "F"
    )

    questions_html = ""
    for i, item in enumerate(breakdown, 1):
        full = item["score_awarded"] >= item["marks"]
        none_ = item["score_awarded"] <= 0
        badge_class = "correct" if full else ("incorrect" if none_ else "partial")
        topic_html = f'<div class="topic">{escape(item["topic"])}</div>' if item.get("topic") else ""
        feedback_html = (
            f'<div class="feedback">Feedback: {escape(item["feedback"])}</div>'
            if item.get("feedback") else ""
        )
        questions_html += f"""
        <div class="question">
            <span class="badge {badge_class}">{item['score_awarded']}/{item['marks']}</span>
            {topic_html}
            <div class="qtext"><span class="qnum">{i}.</span>{escape(item['question'])}</div>
            {feedback_html}
        </div>
        """

    html = f"""
    <html><head><style>{BASE_CSS}</style></head>
    <body>
        <div class="brand">StudyMate</div>
        <h1>Quiz Results</h1>
        <div class="sub">{escape(student_username)} · {escape(quiz.title or 'Quiz')} · {datetime.now().strftime('%d %b %Y')}</div>
        <hr>
        <div class="score-box">
            <div>
                <div class="big">{grade}</div>
                <div class="label">Grade</div>
            </div>
            <div>
                <div class="big">{attempt.total_score}/{attempt.max_score}</div>
                <div class="label">Score</div>
            </div>
            <div>
                <div class="big">{percentage}%</div>
                <div class="label">Percentage</div>
            </div>
        </div>
        <h2>Question Breakdown</h2>
        {questions_html}
    </body></html>
    """
    return HTML(string=html).write_pdf()


def _generate_study_guide_pdf_weasyprint(document, summary, key_concepts, flashcards):
    from weasyprint import HTML

    summary_html = f'<h2>Summary</h2><p class="summary-text">{escape(summary)}</p>' if summary else ""

    concepts_html = ""
    if key_concepts:
        items = "".join(
            f'<div class="concept"><span class="term">{escape(c.get("term", ""))}:</span> {escape(c.get("definition", ""))}</div>'
            for c in key_concepts
        )
        concepts_html = f"<h2>Key Concepts</h2>{items}"

    flashcards_html = ""
    if flashcards:
        items = "".join(
            f'''<div class="card">
                <div class="q">Q: {escape(card.get("question", card.get("front", "")))}</div>
                <div class="a">A: {escape(card.get("answer", card.get("back", "")))}</div>
            </div>'''
            for card in flashcards
        )
        flashcards_html = f"<h2>Flashcards</h2>{items}"

    html = f"""
    <html><head><style>{BASE_CSS}</style></head>
    <body>
        <div class="brand">StudyMate</div>
        <h1>{escape(document.title)}</h1>
        <div class="sub">Study Guide · {datetime.now().strftime('%d %b %Y')}</div>
        <hr>
        {summary_html}
        {concepts_html}
        {flashcards_html}
    </body></html>
    """
    return HTML(string=html).write_pdf()
