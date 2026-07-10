import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  RotateCcw,
  TrendingUp,
  Lightbulb,
  CheckCircle,
  XCircle,
  MinusCircle,
  Download,
} from "lucide-react";
import Layout from "../components/Layout";
import ScoreStamp from "../components/ScoreStamp";
import { api, formatDuration, difficultyLabel, API_URL } from "../api";
import BackButton from "../components/BackButton";

const Results = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { attemptId } = useParams();

  const [result, setResult] = useState(location.state?.result || null);
  const [quiz] = useState(location.state?.quiz || null);
  const [loadingResult, setLoadingResult] = useState(!location.state?.result);
  const [error, setError] = useState("");
  const [explaining, setExplaining] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Derive contextual info from result or quiz state
  const difficulty = quiz?.difficulty || result?.difficulty || null;
  const documentId = quiz?.document_id || result?.document_id || null;

  useEffect(() => {
    if (!location.state?.result && attemptId) {
      api
        .get(`/attempts/${attemptId}`)
        .then((data) => {
          setResult(data);
          setLoadingResult(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoadingResult(false);
        });
    }
  }, [attemptId]);

  const handleExplain = async () => {
    setExplaining(true);
    try {
      const data = await api.post(`/attempts/${attemptId}/explain`);
      setResult((prev) => ({ ...prev, breakdown: data.breakdown }));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setExplaining(false);
    }
  };

  const handleDownloadPdf = async (targetAttemptId) => {
    setDownloadingPdf(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_URL}/attempts/${targetAttemptId}/export-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || "Could not generate the PDF. Try again.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "quiz_results.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loadingResult) {
    return (
      <Layout>
        <BackButton />
        <p className="text-muted text-sm">Loading results...</p>
      </Layout>
    );
  }

  if (error || !result) {
    return (
      <Layout>
        <BackButton />
        <div className="text-center py-16">
          <p className="text-muted mb-4">
            {error || `No results found for attempt #${attemptId}.`}
          </p>
          <Link to="/dashboard" className="text-accent hover:underline">
            Back to dashboard
          </Link>
        </div>
      </Layout>
    );
  }

  const hasMissedMarks = result.breakdown.some(
    (item) => item.score_awarded < item.marks,
  );
  const hasUnexplained = result?.breakdown?.some(
    (item) => item.score_awarded < item.marks && !item.explanation,
  );

  return (
    <Layout>
      <BackButton />

      <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 mb-10">
        <ScoreStamp
          score={result.total_score}
          maxScore={result.max_score}
          percentage={result.percentage}
        />
        <div>
          <h1 className="text-2xl font-semibold mb-1">
            {difficulty
              ? `${difficultyLabel(difficulty)} quiz results`
              : "Results"}
          </h1>
          <p className="text-muted text-sm">
            {result.total_score} / {result.max_score} marks ·{" "}
            {result.percentage}%
          </p>
          {result.study_time_seconds > 0 && (
            <p className="text-muted text-sm mt-1">
              Total study time logged on this document:{" "}
              {formatDuration(result.study_time_seconds)}
            </p>
          )}
          <div className="flex flex-wrap gap-3 mt-3">
            {documentId && (
              <>
                <Link
                  to={`/documents/${documentId}/performance`}
                  className="flex items-center gap-1.5 text-accent text-sm hover:underline"
                >
                  <TrendingUp size={14} /> View progress over time
                </Link>
                <Link
                  to={`/documents/${documentId}/quiz-setup`}
                  className="flex items-center gap-1.5 text-accent text-sm hover:underline"
                >
                  <RotateCcw size={14} /> Retake quiz
                </Link>
                <button
                  onClick={() => handleDownloadPdf(result.attempt_id)}
                  disabled={downloadingPdf}
                  className="flex items-center gap-1.5 text-muted text-sm hover:text-accent transition-colors disabled:opacity-50"
                >
                  <Download size={14} />
                  {downloadingPdf ? "Preparing PDF..." : "Download results PDF"}
                </button>
              </>
            )}
          </div>
          {hasMissedMarks && (
            <button
              onClick={handleExplain}
              disabled={explaining || !hasUnexplained}
              className="mt-4 flex items-center gap-1.5 bg-accent-soft border border-accent/30 text-accent text-sm font-medium rounded-lg px-4 py-2 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Lightbulb size={14} />
              {explaining
                ? "Explaining..."
                : hasUnexplained
                  ? "Explain my mistakes"
                  : "Mistakes explained ↓"}
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {result.breakdown.map((item, idx) => {
          const isMcq = item.type === "mcq";
          const fullMarks = item.score_awarded >= item.marks;
          const noMarks = item.score_awarded <= 0;

          let badgeColor = "border-accent text-accent";
          let StatusIcon = (
            <MinusCircle size={16} className="text-accent shrink-0 mt-0.5" />
          );
          if (fullMarks) {
            badgeColor = "border-correct text-correct";
            StatusIcon = (
              <CheckCircle size={16} className="text-correct shrink-0 mt-0.5" />
            );
          } else if (noMarks) {
            badgeColor = "border-incorrect text-incorrect";
            StatusIcon = (
              <XCircle size={16} className="text-incorrect shrink-0 mt-0.5" />
            );
          }

          return (
            <div
              key={item.question_id}
              className="bg-surface border border-border rounded-xl p-5"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-start gap-2">
                  {StatusIcon}
                  <p className="font-medium leading-relaxed">
                    <span className="font-mono text-accent mr-2">
                      {idx + 1}.
                    </span>
                    {item.question}
                  </p>
                </div>
                <span
                  className={`font-mono text-xs whitespace-nowrap border rounded px-2 py-0.5 shrink-0 ${badgeColor}`}
                >
                  {item.score_awarded}/{item.marks}
                </span>
              </div>

              {isMcq ? (
                <div className="space-y-1.5">
                  {Object.entries(item.options || {}).map(([key, value]) => {
                    let style = "border-border";
                    if (key === item.correct_answer)
                      style = "border-correct bg-correct/10";
                    else if (key === item.user_answer && !item.is_correct)
                      style = "border-incorrect bg-incorrect/10";

                    return (
                      <div
                        key={key}
                        className={`text-sm rounded-lg border px-3 py-1.5 ${style}`}
                      >
                        <span className="font-mono text-muted mr-1">
                          {key}.
                        </span>
                        {value}
                        {key === item.user_answer && (
                          <span className="text-xs text-muted ml-2">
                            (your answer)
                          </span>
                        )}
                        {key === item.correct_answer && (
                          <span className="text-xs text-correct ml-2">
                            (correct)
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-muted text-xs mb-1">Your answer</p>
                    <p className="bg-bg border border-border rounded-lg px-3 py-2 whitespace-pre-wrap">
                      {item.user_answer || (
                        <span className="text-muted">No answer given</span>
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted text-xs mb-1">Feedback</p>
                    <p className="text-ink">{item.feedback}</p>
                  </div>
                  <details className="text-muted">
                    <summary className="cursor-pointer text-xs">
                      Model answer / marking points
                    </summary>
                    <p className="mt-1 text-xs">{item.model_answer}</p>
                  </details>
                </div>
              )}

              {item.explanation && (
                <div className="mt-3 text-sm bg-accent-soft border border-accent/30 rounded-lg px-3 py-2">
                  <p className="text-accent text-xs font-medium mb-1">
                    Why this happened
                  </p>
                  <p className="text-ink">{item.explanation}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-8 flex justify-center">
        <button
          onClick={() => navigate("/dashboard")}
          className="border border-border rounded-lg px-6 py-2.5 hover:border-accent transition-colors"
        >
          Back to dashboard
        </button>
      </div>
    </Layout>
  );
};

export default Results;
