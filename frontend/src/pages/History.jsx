import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, RotateCcw, Clock, BookOpen } from "lucide-react";
import { api, formatDate, formatDuration, gradeFromPercentage, difficultyLabel } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const DIFFICULTY_COLORS = {
  easy: "border-correct text-correct",
  hard: "border-accent text-accent",
  difficult: "border-incorrect text-incorrect",
  lecturer_style: "border-muted text-muted",
};

const History = () => {
  usePageTitle("History");
  const [attempts, setAttempts] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/attempts")
      .then((data) => setAttempts(data.attempts))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1">Quiz history</h1>
      <p className="text-muted text-sm mb-8">Every quiz you've taken, with the option to review or retake.</p>

      {error && <p className="text-incorrect">{error}</p>}

      {!attempts ? (
        <p className="text-muted text-sm">Loading...</p>
      ) : attempts.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-border rounded-xl">
          <BookOpen size={32} className="text-muted mx-auto mb-3" />
          <p className="text-muted mb-4">No quizzes taken yet.</p>
          <Link to="/dashboard" className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity inline-block">
            Go to dashboard
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {attempts.map((a) => (
            <div key={a.id} className="bg-surface border border-border rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="font-mono text-lg w-10 h-10 flex items-center justify-center rounded-full border border-accent/30 bg-accent-soft text-accent shrink-0">
                  {gradeFromPercentage(a.percentage)}
                </div>
                <div className="min-w-0">
                  <p className="font-medium truncate">{a.document_title}</p>
                  <p className="text-xs text-muted flex items-center gap-1.5">
                    <Clock size={11} />
                    {formatDate(a.submitted_at)} · {formatDuration(a.study_time_seconds)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`font-mono text-xs px-2 py-0.5 rounded border ${DIFFICULTY_COLORS[a.difficulty] || "border-border text-muted"}`}>
                  {difficultyLabel(a.difficulty)}
                </span>
                <span className="font-mono text-sm">{a.total_score}/{a.max_score} · {a.percentage}%</span>
                <Link to={`/results/${a.id}`} className="flex items-center gap-1.5 text-sm border border-border rounded-lg px-3 py-1.5 hover:border-accent transition-colors">
                  <Eye size={13} /> Review
                </Link>
                <Link to={`/documents/${a.document_id}/quiz-setup`} className="flex items-center gap-1.5 text-sm bg-accent text-bg font-medium rounded-lg px-3 py-1.5 hover:opacity-90 transition-opacity">
                  <RotateCcw size={13} /> Retake
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default History;
