import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, difficultyLabel } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const STAGES = [
  {
    key: "easy",
    label: "Stage 1 — Easy",
    tag: "Practice",
    description:
      "Direct recall, definitions, and simple concept checks. MCQ only. Tests whether you know the material at all.",
    color: "border-correct text-correct",
  },
  {
    key: "hard",
    label: "Stage 2 — Hard",
    tag: "Objective",
    description:
      "Twisted MCQs — NOT/EXCEPT phrasing, near-identical options, scenario-based questions, compare A vs B. MCQ only. Tests deeper understanding.",
    color: "border-accent text-accent",
  },
  {
    key: "difficult",
    label: "Stage 3 — Difficult",
    tag: "Final exam",
    description:
      "MCQ + theory combined. Objective side = 60%, theory side = 40%. Feels like a real final exam.",
    color: "border-incorrect text-incorrect",
  },
  {
    key: "lecturer_style",
    label: "Question Pattern Trainer",
    tag: "Custom",
    description:
      "Upload 3–5 past questions from a lecturer. StudyMate learns how they write and twist questions, then generates new practice questions from your material in that exact pattern.",
    color: "border-muted text-muted",
  },
];

const QuizSetup = () => {
  usePageTitle("Quiz setup");
  const { id } = useParams();
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [difficulty, setDifficulty] = useState("easy");
  const [formatMode, setFormatMode] = useState(40); // default Easy format A
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [recommendation, setRecommendation] = useState(null);
  const [dismissedRecommendation, setDismissedRecommendation] = useState(false);
  const [otherDocuments, setOtherDocuments] = useState(null);
  const [styleDocumentId, setStyleDocumentId] = useState("");

  useEffect(() => {
    api.get("/quizzes/config").then(setConfig).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    api
      .get("/documents")
      .then((data) => {
        setOtherDocuments(
          data.documents.filter((d) => String(d.id) !== String(id))
        );
      })
      .catch(() => setOtherDocuments([]));
  }, [id]);

  useEffect(() => {
    api
      .get(`/documents/${id}/recommended-difficulty`)
      .then((data) => {
        setDifficulty((current) => {
          if (data.recommendation && current === "easy") {
            setRecommendation(data.recommendation);
            return data.recommendation.suggested_difficulty;
          }
          if (data.recommendation) setRecommendation(data.recommendation);
          return current;
        });
      })
      .catch(() => {});
  }, [id]);

  // When stage changes, default to the larger format option for that stage
  const handleStageChange = (key) => {
    setDifficulty(key);
    setError("");
    if (key === "easy") setFormatMode(40);
    else setFormatMode(60);
  };

  // Get the available format options for the current stage from config
  const currentFormats = config
    ? config[difficulty === "lecturer_style" ? "pattern_trainer" : difficulty] ?? []
    : [];

  const selectedFormat = currentFormats.find(
    (f) => f.format_mode === formatMode
  ) || currentFormats[0];

  const handleStart = async () => {
    setCreating(true);
    setError("");
    try {
      let quiz;
      if (difficulty === "lecturer_style") {
        if (!styleDocumentId) {
          setError("Choose a past-questions document first.");
          setCreating(false);
          return;
        }
        quiz = await api.post("/quizzes/lecturer-style", {
          content_document_id: Number(id),
          style_document_id: Number(styleDocumentId),
          format_mode: formatMode,
        });
      } else {
        quiz = await api.post("/quizzes", {
          document_id: Number(id),
          difficulty,
          format_mode: formatMode,
        });
      }
      navigate(`/quiz/${quiz.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1">Set up your quiz</h1>
      <p className="text-muted text-sm mb-8">
        Choose a stage. Each one is generated fresh from your document.
      </p>

      {recommendation && !dismissedRecommendation && (
        <div className="flex items-start justify-between gap-3 bg-accent-soft border border-accent/30 rounded-xl px-4 py-3 mb-6">
          <p className="text-sm">
            {recommendation.direction === "up" ? (
              <>
                You've averaged{" "}
                <span className="font-mono text-accent">
                  {recommendation.average_percentage}%
                </span>{" "}
                on your last {recommendation.based_on_attempts}{" "}
                {difficultyLabel(recommendation.current_difficulty)} quizzes —
                you might be ready for{" "}
                <span className="font-semibold">
                  {difficultyLabel(recommendation.suggested_difficulty)}
                </span>
                .
              </>
            ) : (
              <>
                Your last {recommendation.based_on_attempts}{" "}
                {difficultyLabel(recommendation.current_difficulty)} quizzes
                averaged{" "}
                <span className="font-mono text-accent">
                  {recommendation.average_percentage}%
                </span>{" "}
                — stepping down to{" "}
                <span className="font-semibold">
                  {difficultyLabel(recommendation.suggested_difficulty)}
                </span>{" "}
                might help you rebuild from a stronger base.
              </>
            )}
          </p>
          <button
            onClick={() => setDismissedRecommendation(true)}
            className="text-muted hover:text-ink text-sm shrink-0"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {/* Stage cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {STAGES.map((stage) => (
          <button
            key={stage.key}
            onClick={() => handleStageChange(stage.key)}
            className={`text-left rounded-xl p-5 border transition-colors ${
              difficulty === stage.key
                ? "border-accent bg-accent-soft"
                : "border-border bg-surface hover:border-muted"
            }`}
          >
            <span
              className={`font-mono text-[10px] uppercase tracking-wider border rounded-full px-2 py-0.5 mb-2 inline-block ${stage.color}`}
            >
              {stage.tag}
            </span>
            <p className="font-semibold text-sm mb-1">{stage.label}</p>
            <p className="text-xs text-muted leading-relaxed">
              {stage.description}
            </p>
          </button>
        ))}
      </div>

      {/* Format picker + stats for the selected stage */}
      {config && difficulty !== "lecturer_style" && currentFormats.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5 mb-6">
          <p className="text-sm text-muted mb-3 font-mono">Choose a format:</p>
          <div className="flex flex-wrap gap-3 mb-4">
            {currentFormats.map((fmt) => (
              <button
                key={fmt.format_mode}
                onClick={() => setFormatMode(fmt.format_mode)}
                className={`rounded-lg px-4 py-2 border text-sm font-mono transition-colors ${
                  formatMode === fmt.format_mode
                    ? "border-accent text-accent bg-accent-soft"
                    : "border-border text-muted hover:border-muted"
                }`}
              >
                {fmt.mcq_count}Q × {fmt.mcq_marks} mark
                {fmt.mcq_marks > 1 ? "s" : ""}
              </button>
            ))}
          </div>
          {selectedFormat && (
            <div className="font-mono text-xs text-muted space-y-1">
              <p>
                {selectedFormat.mcq_count} objective questions
                {selectedFormat.theory_count > 0
                  ? ` + ${selectedFormat.theory_count} theory questions`
                  : ""}
              </p>
              <p>
                {selectedFormat.mcq_count * selectedFormat.mcq_marks} objective marks
                {selectedFormat.theory_count > 0
                  ? ` + ${selectedFormat.theory_count * selectedFormat.theory_marks} theory marks`
                  : ""}
                {" "}= <span className="text-ink">{selectedFormat.total_marks} marks total</span>
              </p>
              <p>{selectedFormat.time_limit_minutes} minutes</p>
            </div>
          )}
        </div>
      )}

      {/* Pattern Trainer config panel */}
      {difficulty === "lecturer_style" && (
        <div className="bg-surface border border-border rounded-xl p-5 mb-6 space-y-4">
          {/* Format picker for pattern trainer */}
          {config && currentFormats.length > 0 && (
            <div>
              <p className="text-sm text-muted mb-2 font-mono">Choose a format:</p>
              <div className="flex flex-wrap gap-3 mb-3">
                {currentFormats.map((fmt) => (
                  <button
                    key={fmt.format_mode}
                    onClick={() => setFormatMode(fmt.format_mode)}
                    className={`rounded-lg px-4 py-2 border text-sm font-mono transition-colors ${
                      formatMode === fmt.format_mode
                        ? "border-accent text-accent bg-accent-soft"
                        : "border-border text-muted hover:border-muted"
                    }`}
                  >
                    {fmt.mcq_count}Q × {fmt.mcq_marks} mark
                    {fmt.mcq_marks > 1 ? "s" : ""}
                  </button>
                ))}
              </div>
              {selectedFormat && (
                <p className="font-mono text-xs text-muted">
                  {selectedFormat.total_marks} marks · {selectedFormat.time_limit_minutes} min · MCQ only
                </p>
              )}
            </div>
          )}

          {/* Past questions document selector */}
          <div>
            <label className="block text-sm text-muted mb-2">
              Past questions document
            </label>
            {otherDocuments === null ? (
              <p className="text-sm text-muted">Loading your documents...</p>
            ) : otherDocuments.length === 0 ? (
              <div className="text-center py-4 border border-dashed border-border rounded-lg">
                <p className="text-sm mb-1">No other documents uploaded yet.</p>
                <p className="text-xs text-muted">
                  Upload 3–5 past questions from a lecturer from your Dashboard
                  (PDF, Word, or pasted text), then come back here.
                </p>
              </div>
            ) : (
              <select
                value={styleDocumentId}
                onChange={(e) => setStyleDocumentId(e.target.value)}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
              >
                <option value="">Choose a document with past questions...</option>
                {otherDocuments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
      )}

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mb-6">
          {error}
        </p>
      )}

      <button
        onClick={handleStart}
        disabled={
          creating ||
          !config ||
          (difficulty === "lecturer_style" &&
            (otherDocuments?.length === 0 || !styleDocumentId))
        }
        className="bg-accent text-bg font-semibold rounded-lg px-6 py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {creating ? "Generating quiz..." : "Generate quiz"}
      </button>
      {creating && (
        <p className="text-xs text-muted mt-3">
          This can take up to a minute for longer quizzes — the AI is writing every question fresh from your material.
        </p>
      )}
    </Layout>
  );
};

export default QuizSetup;
