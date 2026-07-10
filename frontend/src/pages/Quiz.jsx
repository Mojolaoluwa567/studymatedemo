import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { api, difficultyLabel } from "../api";
import Layout from "../components/Layout";
import ReportCardModal from "../components/ReportCardModal";

function formatClock(seconds) {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

const Quiz = () => {
  const { quizId } = useParams();
  const navigate = useNavigate();

  const [quiz, setQuiz] = useState(null);
  const [remaining, setRemaining] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const attemptIdRef = useRef(null);
  const answersRef = useRef({});
  const submittedRef = useRef(false);
  const timerRef = useRef(null);
  const quizRef = useRef(null);
  const timeLimitSecondsRef = useRef(0);
  const remainingRef = useRef(0);

  const [reportResult, setReportResult] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const currentIndexRef = useRef(0);

  // Gated flow state (Stage 3 — Difficult only)
  const [phase, setPhase] = useState(null);
  const phaseRef = useRef(null);
  const [theoryQuestions, setTheoryQuestions] = useState([]);
  const [mcqResult, setMcqResult] = useState(null);
  const [submittingMcq, setSubmittingMcq] = useState(false);

  const setAnswer = (questionId, value) => {
    setAnswers((prev) => {
      const next = { ...prev, [questionId]: value };
      answersRef.current = next;
      return next;
    });
  };

  const handleSubmit = async (skipConfirm = false) => {
    if (submittedRef.current) return;

    if (!skipConfirm) {
      const allQuestions = quizRef.current?.questions || [];
      // For gated flow in theory phase, only count theory questions
      const phaseQuestions =
        phase === "theory"
          ? allQuestions.filter((q) => q.type === "theory")
          : allQuestions;
      const answeredNow = phaseQuestions.filter(
        (q) =>
          answersRef.current[q.id] !== undefined &&
          answersRef.current[q.id] !== "",
      ).length;
      if (answeredNow < phaseQuestions.length) {
        const unanswered = phaseQuestions.length - answeredNow;
        toast(
          (t) => (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">
                {unanswered} question{unanswered === 1 ? "" : "s"} unanswered
              </p>
              <p className="text-xs text-muted">Submit anyway?</p>
              <div className="flex gap-2 mt-1">
                <button
                  onClick={() => {
                    toast.dismiss(t.id);
                    doSubmit();
                  }}
                  className="text-xs bg-accent text-bg rounded px-3 py-1.5 font-medium"
                >
                  Submit
                </button>
                <button
                  onClick={() => toast.dismiss(t.id)}
                  className="text-xs border border-border rounded px-3 py-1.5"
                >
                  Keep going
                </button>
              </div>
            </div>
          ),
          { duration: 15000 },
        );
        return; // wait for user choice in the toast
      }
    }

    doSubmit();
  };

  const doSubmit = async () => {
    if (submittedRef.current) return;

    submittedRef.current = true;
    clearInterval(timerRef.current);
    setSubmitting(true);

    try {
      const payload = {
        answers: Object.entries(answersRef.current).map(
          ([question_id, answer]) => ({
            question_id: Number(question_id),
            answer,
          }),
        ),
      };
      const result = await api.post(
        `/attempts/${attemptIdRef.current}/submit`,
        payload,
      );
      setReportResult(result);

      for (const achievement of result.new_achievements || []) {
        toast.success(`Achievement unlocked: ${achievement.title}`, {
          icon: "🏆",
          duration: 5000,
        });
      }
    } catch (err) {
      setError(err.message);
      submittedRef.current = false;
      setSubmitting(false);
    }
  };

  const doSubmitMcq = async () => {
    setSubmittingMcq(true);
    try {
      const mcqAnswers = Object.entries(answersRef.current).map(
        ([question_id, answer]) => ({
          question_id: Number(question_id),
          answer,
        }),
      );
      const result = await api.post(
        `/attempts/${attemptIdRef.current}/submit-mcq`,
        { answers: mcqAnswers },
      );
      setMcqResult(result);
      setTheoryQuestions(result.theory_questions || []);
      // Clear answers for the theory phase and reset navigation
      setAnswers({});
      answersRef.current = {};
      setCurrentIndex(0);
      currentIndexRef.current = 0;
      setPhase("theory");
      phaseRef.current = "theory";
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmittingMcq(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      try {
        const quizData = await api.get(`/quizzes/${quizId}`);
        const attempt = await api.post("/attempts", {
          quiz_id: Number(quizId),
        });
        if (cancelled) return;

        setQuiz(quizData);
        quizRef.current = quizData;
        attemptIdRef.current = attempt.attempt_id;

        // Detect gated flow: quiz has both MCQ and theory questions
        const hasTheory = quizData.questions.some((q) => q.type === "theory");
        if (hasTheory) {
          if (attempt.mcq_already_submitted) {
            // Resuming an attempt where MCQ was already submitted before
            // they navigated away or refreshed — skip straight to the
            // theory phase instead of asking them to redo the MCQs.
            setPhase("theory");
            phaseRef.current = "theory";
            setMcqResult({ mcq_score: attempt.mcq_score });
            setTheoryQuestions(
              quizData.questions.filter((q) => q.type === "theory"),
            );
          } else {
            setPhase("mcq");
            phaseRef.current = "mcq";
          }
        }

        if (attempt.resumed) {
          toast("Resuming your in-progress attempt.", { icon: "⏱️" });
        }

        const limitSeconds = attempt.time_limit_minutes * 60;
        const alreadyElapsed = attempt.elapsed_seconds || 0;
        const actualRemaining = Math.max(0, limitSeconds - alreadyElapsed);
        timeLimitSecondsRef.current = limitSeconds;
        remainingRef.current = actualRemaining;
        setRemaining(actualRemaining);

        timerRef.current = setInterval(() => {
          setRemaining((prev) => {
            if (prev <= 1) {
              clearInterval(timerRef.current);
              remainingRef.current = 0;
              // If timer expires during MCQ phase, submit MCQ then immediately
              // submit empty theory — the student gets what they answered
              if (phaseRef.current === "mcq") {
                doSubmitMcq().then(() => doSubmit());
              } else {
                doSubmit();
              }
              return 0;
            }
            remainingRef.current = prev - 1;
            return prev - 1;
          });
        }, 1000);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };

    init();
    return () => {
      cancelled = true;
      clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId]);

  // Keyboard shortcuts: arrow keys to move between questions, number keys
  // (1-4) to pick an MCQ option. Ignored entirely while typing in the
  // theory-answer textarea, so a student writing "in 1990..." or using
  // arrow keys to move their cursor doesn't accidentally navigate away
  // from the question they're answering.
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = e.target.tagName;
      if (tag === "TEXTAREA" || tag === "INPUT") return;
      if (!quizRef.current) return;

      const total = quizRef.current.questions.length;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = Math.min(total - 1, currentIndexRef.current + 1);
        currentIndexRef.current = next;
        setCurrentIndex(next);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const next = Math.max(0, currentIndexRef.current - 1);
        currentIndexRef.current = next;
        setCurrentIndex(next);
      } else if (["1", "2", "3", "4"].includes(e.key)) {
        const q = quizRef.current.questions[currentIndexRef.current];
        if (q && q.type === "mcq") {
          const keys = Object.keys(q.options);
          const optionKey = keys[Number(e.key) - 1];
          if (optionKey) setAnswer(q.id, optionKey);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <Layout>
        <p className="text-incorrect">{error}</p>
      </Layout>
    );
  }

  if (!quiz || remaining === null) {
    return (
      <Layout>
        <p className="text-muted text-sm">Generating your quiz...</p>
      </Layout>
    );
  }

  const lowTime = remaining <= 60;

  // Phase-aware question list: in gated flow, only show MCQ questions
  // during the MCQ phase, then only theory questions during theory phase.
  // For non-gated quizzes (Easy/Hard/Pattern Trainer), show everything.
  const activeQuestions =
    phase === "mcq"
      ? quiz.questions.filter((q) => q.type === "mcq")
      : phase === "theory"
        ? theoryQuestions
        : quiz.questions;

  const currentQuestion = activeQuestions[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === activeQuestions.length - 1;
  const answeredCount = Object.keys(answers).filter((id) =>
    activeQuestions.some((q) => String(q.id) === id && answers[id] !== ""),
  ).length;

  const goTo = (index) => {
    const clamped = Math.max(0, Math.min(activeQuestions.length - 1, index));
    currentIndexRef.current = clamped;
    setCurrentIndex(clamped);
  };

  return (
    <>
      <Layout>
        <div className="sticky top-0 bg-bg/95 backdrop-blur border-b border-border -mx-4 px-4 py-3 mb-6 flex items-center justify-between z-10">
          <div>
            <p className="text-sm text-muted">
              {difficultyLabel(quiz.difficulty)} · {quiz.total_marks} marks
            </p>
            {phase === "mcq" && (
              <p className="text-xs text-accent font-mono">
                Section 1 of 2 — Objective questions
              </p>
            )}
            {phase === "theory" && (
              <p className="text-xs text-accent font-mono">
                Section 2 of 2 — Theory questions
                {mcqResult && (
                  <span className="text-muted ml-2">
                    (MCQ: {mcqResult.mcq_score}/{mcqResult.mcq_max})
                  </span>
                )}
              </p>
            )}
          </div>
          <span
            className={`font-mono text-xl tabular-nums ${
              lowTime ? "text-incorrect" : "text-accent"
            }`}
          >
            {formatClock(remaining)}
          </span>
        </div>

        {/* Phase transition banner shown when entering theory section */}
        {phase === "theory" && mcqResult && (
          <div className="bg-accent-soft border border-accent/30 rounded-xl px-4 py-3 mb-6">
            <p className="text-sm font-medium">
              Objective section complete —{" "}
              <span className="text-accent">
                {mcqResult.mcq_score}/{mcqResult.mcq_max} marks (
                {mcqResult.mcq_percentage}%)
              </span>
            </p>
            <p className="text-xs text-muted mt-0.5">
              Now answer the theory questions below. Your final score will
              combine both sections.
            </p>
          </div>
        )}

        {/* Progress dots */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs text-muted font-mono">
            Question {currentIndex + 1} of {activeQuestions.length}
          </p>
          <p className="text-xs text-muted font-mono">
            {answeredCount} of {activeQuestions.length} answered
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5 mb-6">
          {activeQuestions.map((q, idx) => {
            const isAnswered =
              answers[q.id] !== undefined && answers[q.id] !== "";
            const isCurrent = idx === currentIndex;
            return (
              <button
                key={q.id}
                onClick={() => goTo(idx)}
                aria-label={`Go to question ${idx + 1}`}
                className={`w-7 h-7 rounded-full text-xs font-mono flex items-center justify-center border transition-colors ${
                  isCurrent
                    ? "border-accent bg-accent text-bg font-semibold"
                    : isAnswered
                      ? "border-correct/40 bg-correct/10 text-correct"
                      : "border-border text-muted hover:border-muted"
                }`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>

        {/* Single question card */}
        <div className="bg-surface border border-border rounded-xl p-5 min-h-[280px]">
          <div className="flex items-start justify-between gap-3 mb-4">
            <p className="font-medium leading-relaxed text-lg">
              <span className="font-mono text-accent mr-2">
                {currentIndex + 1}.
              </span>
              {currentQuestion.question}
            </p>
            <span className="font-mono text-xs text-muted whitespace-nowrap border border-border rounded px-2 py-0.5">
              {currentQuestion.marks} mark
              {currentQuestion.marks === 1 ? "" : "s"}
            </span>
          </div>

          {currentQuestion.type === "mcq" ? (
            <div className="space-y-2">
              {Object.entries(currentQuestion.options).map(([key, value]) => (
                <label
                  key={key}
                  className={`flex items-start gap-3 rounded-lg border px-3 py-2 cursor-pointer transition-colors ${
                    answers[currentQuestion.id] === key
                      ? "border-accent bg-accent-soft"
                      : "border-border hover:border-muted"
                  }`}
                >
                  <input
                    type="radio"
                    name={`question-${currentQuestion.id}`}
                    value={key}
                    checked={answers[currentQuestion.id] === key}
                    onChange={() => setAnswer(currentQuestion.id, key)}
                    className="mt-1 accent-[rgb(var(--color-accent))]"
                  />
                  <span className="text-sm">
                    <span className="font-mono text-muted mr-1">{key}.</span>
                    {value}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <textarea
              value={answers[currentQuestion.id] || ""}
              onChange={(e) => setAnswer(currentQuestion.id, e.target.value)}
              placeholder="Type your answer..."
              rows={6}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors resize-y"
            />
          )}
        </div>

        {/* Navigation */}
        <div className="mt-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <button
            onClick={() => goTo(currentIndex - 1)}
            disabled={isFirst}
            className="border border-border rounded-lg px-5 py-2.5 hover:border-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed order-2 sm:order-1"
          >
            ← Previous
          </button>

          <div className="flex items-center gap-3 order-1 sm:order-2 justify-between sm:justify-end">
            {/* Submit now — always visible, but not shown in MCQ phase
              (students can't skip to the end of a gated exam early) */}
            {!phase && (
              <button
                onClick={() => handleSubmit()}
                disabled={submitting}
                className="text-sm text-muted hover:text-incorrect transition-colors disabled:opacity-50 shrink-0"
              >
                Submit now
              </button>
            )}

            {!isLast ? (
              <button
                onClick={() => goTo(currentIndex + 1)}
                className="bg-accent text-bg font-semibold rounded-lg px-4 sm:px-6 py-2.5 hover:opacity-90 transition-opacity flex-1 sm:flex-none"
              >
                Next →
              </button>
            ) : phase === "mcq" ? (
              // Last MCQ in gated flow → submit MCQ section
              <button
                onClick={doSubmitMcq}
                disabled={submittingMcq}
                className="bg-accent text-bg font-semibold rounded-lg px-4 sm:px-6 py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50 flex-1 sm:flex-none text-sm sm:text-base"
              >
                {submittingMcq ? "Submitting..." : "Submit objective section →"}
              </button>
            ) : (
              // Last question in theory phase or non-gated quiz → final submit
              <button
                onClick={() => handleSubmit()}
                disabled={submitting}
                className="bg-accent text-bg font-semibold rounded-lg px-4 sm:px-6 py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50 flex-1 sm:flex-none"
              >
                {submitting ? "Submitting..." : "Submit quiz"}
              </button>
            )}
          </div>
        </div>

        <p className="hidden sm:block text-center text-xs text-muted font-mono mt-4">
          ← → to navigate · 1-4 to select an answer
        </p>
      </Layout>

      {reportResult && (
        <ReportCardModal
          result={reportResult}
          attemptId={attemptIdRef.current}
          timeSpentSeconds={timeLimitSecondsRef.current - remainingRef.current}
          onViewResult={() =>
            navigate(`/results/${attemptIdRef.current}`, {
              state: { result: reportResult, quiz: quizRef.current },
              replace: true,
            })
          }
          onRetake={() =>
            navigate(`/documents/${quizRef.current.document_id}/quiz-setup`)
          }
          onClose={() => navigate("/dashboard")}
        />
      )}
    </>
  );
};

export default Quiz;
