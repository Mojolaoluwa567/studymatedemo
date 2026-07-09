from types import SimpleNamespace
from grading import grade_mcq


def test_grade_mcq_correct_uppercase_match():
    question = SimpleNamespace(correct_answer="B", marks=2)
    score, is_correct = grade_mcq(question, "B")
    assert score == 2
    assert is_correct is True


def test_grade_mcq_case_insensitive():
    question = SimpleNamespace(correct_answer="b", marks=3)
    score, is_correct = grade_mcq(question, "B")
    assert score == 3
    assert is_correct is True


def test_grade_mcq_incorrect():
    question = SimpleNamespace(correct_answer="A", marks=5)
    score, is_correct = grade_mcq(question, "C")
    assert score == 0
    assert is_correct is False


def test_grade_mcq_no_answer():
    question = SimpleNamespace(correct_answer="A", marks=5)
    score, is_correct = grade_mcq(question, None)
    assert score == 0
    assert is_correct is False


def test_grade_mcq_whitespace_and_case_tolerant():
    question = SimpleNamespace(correct_answer="D", marks=1)
    score, is_correct = grade_mcq(question, "  d  ")
    assert score == 1
    assert is_correct is True