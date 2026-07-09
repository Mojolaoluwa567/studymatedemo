from models import User, Document, Quiz, Question


def _signup_and_login(client, username):
    client.post("/signup", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "StrongPass1!",
    })
    resp = client.post("/login", json={"username": username, "password": "StrongPass1!"})
    return resp.get_json()["access_token"]


def _make_difficult_quiz(db, user_id):
    doc = Document(
        user_id=user_id, title="Doc", filename="doc.pdf",
        text_content="text", source_type="pdf",
    )
    db.session.add(doc)
    db.session.commit()

    quiz = Quiz(
        document_id=doc.id, user_id=user_id, difficulty="difficult",
        num_questions=2, total_marks=8, time_limit_minutes=20,
    )
    db.session.add(quiz)
    db.session.flush()

    mcq = Question(
        quiz_id=quiz.id, order_index=0, type="mcq", question_text="2+2?",
        options={"A": "3", "B": "4"}, correct_answer="B", marks=3,
    )
    theory = Question(
        quiz_id=quiz.id, order_index=1, type="theory",
        question_text="Explain X.", correct_answer="Model answer about X.",
        marks=5,
    )
    db.session.add_all([mcq, theory])
    db.session.commit()
    return quiz


def test_gated_mcq_then_theory_submit(app, client, db, monkeypatch):
    token = _signup_and_login(client, "gateduser")
    user = User.query.filter_by(username="gateduser").first()
    quiz = _make_difficult_quiz(db, user.id)
    headers = {"Authorization": f"Bearer {token}"}

    start_resp = client.post("/attempts", json={"quiz_id": quiz.id}, headers=headers)
    assert start_resp.status_code == 200
    attempt_id = start_resp.get_json()["attempt_id"]

    mcq_question = [q for q in quiz.questions if q.type == "mcq"][0]
    mcq_resp = client.post(
        f"/attempts/{attempt_id}/submit-mcq",
        json={"answers": [{"question_id": mcq_question.id, "answer": "B"}]},
        headers=headers,
    )
    assert mcq_resp.status_code == 200
    mcq_data = mcq_resp.get_json()
    assert mcq_data["mcq_score"] == 3
    assert len(mcq_data["theory_questions"]) == 1

    # Stub the AI grading call so the test doesn't hit Gemini for real
    monkeypatch.setattr(
        "app.grade_theory_batch",
        lambda items: [{"score": 4, "feedback": "Good, missed one point."}],
    )

    theory_question = [q for q in quiz.questions if q.type == "theory"][0]
    submit_resp = client.post(
        f"/attempts/{attempt_id}/submit",
        json={"answers": [{"question_id": theory_question.id, "answer": "My explanation."}]},
        headers=headers,
    )
    assert submit_resp.status_code == 200
    result = submit_resp.get_json()
    assert result["total_score"] == 7      # 3 (mcq) + 4 (theory)
    assert result["max_score"] == 8
    assert result["percentage"] == 87.5


def test_submit_without_mcq_first_is_rejected(app, client, db):
    token = _signup_and_login(client, "gateduser2")
    user = User.query.filter_by(username="gateduser2").first()
    quiz = _make_difficult_quiz(db, user.id)
    headers = {"Authorization": f"Bearer {token}"}

    start_resp = client.post("/attempts", json={"quiz_id": quiz.id}, headers=headers)
    attempt_id = start_resp.get_json()["attempt_id"]

    theory_question = [q for q in quiz.questions if q.type == "theory"][0]
    resp = client.post(
        f"/attempts/{attempt_id}/submit",
        json={"answers": [{"question_id": theory_question.id, "answer": "..."}]},
        headers=headers,
    )
    assert resp.status_code == 400