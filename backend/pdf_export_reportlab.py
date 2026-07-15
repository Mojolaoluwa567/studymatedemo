"""
PDF export for StudyMate - results cards and study guides.
Uses reportlab (already installed for test fixtures).
"""
import io
from datetime import datetime


def generate_results_pdf_reportlab(attempt, quiz, breakdown, student_username):
    """
    Generates a printable results/report card PDF for a completed quiz attempt.
    Returns bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.units import cm
    

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    ACCENT = HexColor("#6366F1")
    CORRECT = HexColor("#22c55e")
    INCORRECT = HexColor("#ef4444")
    LIGHT_GRAY = HexColor("#f1f5f9")
    MID_GRAY = HexColor("#94a3b8")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=20, textColor=ACCENT, spaceAfter=4)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=MID_GRAY, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=13, textColor=black, spaceBefore=16, spaceAfter=8)
    q_style = ParagraphStyle("q", parent=styles["Normal"], fontSize=10, spaceAfter=4, leftIndent=12)

    story = []

    story.append(Paragraph("StudyMate", ParagraphStyle("brand", parent=styles["Normal"], fontSize=9, textColor=ACCENT)))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Quiz Results", title_style))
    story.append(Paragraph(f"Student: {student_username} · {quiz.title or 'Quiz'} · {datetime.now().strftime('%d %b %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 12))

    percentage = attempt.percentage or 0
    grade = "A" if percentage >= 70 else "B" if percentage >= 60 else "C" if percentage >= 50 else "D" if percentage >= 40 else "F"
    score_data = [
        ["Score", "Grade", "Max Marks"],
        [f"{attempt.total_score}/{attempt.max_score}", grade, str(attempt.max_score)],
    ]
    score_table = Table(score_data, colWidths=[5*cm, 5*cm, 5*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), ACCENT),
        ("TEXTCOLOR", (0,0), (-1,0), white),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("FONTSIZE", (0,1), (-1,1), 18),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_GRAY]),
        ("ROWHEIGHT", (0,1), (-1,-1), 32),
        ("GRID", (0,0), (-1,-1), 0.5, MID_GRAY),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Question Breakdown", section_style))
    for i, item in enumerate(breakdown, 1):
        full = item["score_awarded"] >= item["marks"]
        none_ = item["score_awarded"] <= 0
        color = CORRECT if full else (INCORRECT if none_ else ACCENT)
        mark_str = f"{item['score_awarded']}/{item['marks']}"
        if item.get("topic"):
            story.append(Paragraph(f"<font color='#94a3b8'>[{item['topic']}]</font>", ParagraphStyle("topic", parent=styles["Normal"], fontSize=8, spaceAfter=1)))
        hex_str = color.hexval()[2:]  # strip the "0x" prefix, e.g. "0x22c55e" -> "22c55e"
        story.append(Paragraph(
            f"<b>{i}.</b> {item['question']} "
            f"<font color='#{hex_str}'><b>({mark_str})</b></font>",
            q_style
        ))
        if item.get("feedback"):
            story.append(Paragraph(f"<i>Feedback: {item['feedback']}</i>", ParagraphStyle("fb", parent=styles["Normal"], fontSize=9, textColor=MID_GRAY, leftIndent=20, spaceAfter=8)))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def generate_study_guide_pdf_reportlab(document, summary, key_concepts, flashcards):
    """
    Generates a printable study guide PDF from a document's AI study aids.
    Returns bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    ACCENT = HexColor("#6366F1")
    MID_GRAY = HexColor("#94a3b8")
    LIGHT_GRAY = HexColor("#f1f5f9")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=20, textColor=ACCENT, spaceAfter=4)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=MID_GRAY, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=13, spaceAfter=8, spaceBefore=16)
    body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, spaceAfter=6, leading=15)
    bullet_style = ParagraphStyle("bullet", parent=styles["Normal"], fontSize=10, spaceAfter=5, leftIndent=16, leading=14)

    story = []
    story.append(Paragraph("StudyMate", ParagraphStyle("brand", parent=styles["Normal"], fontSize=9, textColor=ACCENT)))
    story.append(Spacer(1, 6))
    story.append(Paragraph(document.title, title_style))
    story.append(Paragraph(f"Study Guide · {datetime.now().strftime('%d %b %Y')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
    story.append(Spacer(1, 12))

    if summary:
        story.append(Paragraph("Summary", section_style))
        story.append(Paragraph(summary, body_style))

    if key_concepts:
        story.append(Paragraph("Key Concepts", section_style))
        for c in key_concepts:
            story.append(Paragraph(f"<b>{c.get('term', '')}:</b> {c.get('definition', '')}", bullet_style))

    if flashcards:
        story.append(Paragraph("Flashcards", section_style))
        for card in flashcards:
            story.append(Paragraph(f"<b>Q:</b> {card.get('question', card.get('front', ''))}", bullet_style))
            story.append(Paragraph(f"<b>A:</b> {card.get('answer', card.get('back', ''))}", ParagraphStyle("ans", parent=styles["Normal"], fontSize=10, spaceAfter=10, leftIndent=16, textColor=HexColor("#334155"))))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def generate_gradebook_pdf_reportlab(class_name, students):
    """Fallback gradebook PDF using reportlab. Returns bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    ACCENT = HexColor("#6366F1")
    LIGHT_GRAY = HexColor("#f1f5f9")
    MID_GRAY = HexColor("#94a3b8")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18, textColor=black, spaceAfter=4)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=MID_GRAY, spaceAfter=12)

    story = [
        Paragraph("StudyMate", ParagraphStyle("brand", parent=styles["Normal"], fontSize=9, textColor=ACCENT)),
        Spacer(1, 6),
        Paragraph(f"Gradebook — {class_name}", title_style),
        Paragraph(f"Generated {datetime.now().strftime('%d %b %Y')}", sub_style),
        Spacer(1, 8),
    ]

    table_data = [["Student", "Attempts", "Average"]]
    for s in students:
        table_data.append([s["username"], str(s["attempts_count"]), f"{s['average_percentage']}%"])

    table = Table(table_data, colWidths=[7*cm, 4*cm, 4*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 0), (-1, 0), MID_GRAY),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
    ]))
    story.append(table)

    doc.build(story)
    return buf.getvalue()