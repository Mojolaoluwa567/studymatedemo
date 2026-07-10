import React, { useEffect } from "react";
import confetti from "canvas-confetti";
import ScoreStamp from "./ScoreStamp";
import { gradeFromPercentage, formatClock, API_URL } from "../api";

const ReportCardModal = ({
  result,
  timeSpentSeconds,
  onReviewAnswers,
  onRetake,
  onClose,
  attemptId,
}) => {
  const [downloadingPdf, setDownloadingPdf] = React.useState(false);
  const correctCount = result.breakdown.filter(
    (q) => q.type === "mcq" && q.is_correct,
  ).length;
  const incorrectCount = result.breakdown.filter(
    (q) => q.type === "mcq" && !q.is_correct,
  ).length;
  const theoryCount = result.breakdown.filter(
    (q) => q.type === "theory",
  ).length;
  const grade = gradeFromPercentage(result.percentage);

  useEffect(() => {
    if (result.percentage >= 80) {
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 },
        colors: ["#818CF8", "#34D399", "#FBBF24"],
      });
    }
  }, [result.percentage]);

  const handleDownload = async () => {
    setDownloadingPdf(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_URL}/attempts/${attemptId}/export-pdf`,
        { headers: { Authorization: `Bearer ${token}` } },
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
      console.error(err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  let summary = "Keep practicing - reviewing your mistakes will help most.";
  if (result.percentage >= 80)
    summary = "Excellent work! You've got a strong grasp of this material.";
  else if (result.percentage >= 60)
    summary = "Good effort - a bit more review and you'll be solid.";
  else if (result.percentage >= 45)
    summary = "You're getting there - focus on the topics you missed.";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="bg-surface border border-border rounded-2xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex flex-col items-center text-center mb-6">
          <ScoreStamp
            score={result.total_score}
            maxScore={result.max_score}
            percentage={result.percentage}
          />
          <h2 className="text-xl font-semibold mt-4">Quiz complete!</h2>
          <p className="font-mono text-3xl text-accent mt-1">Grade: {grade}</p>
          <p className="text-muted text-sm mt-2">{summary}</p>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-6 text-sm">
          <div className="bg-bg border border-border rounded-lg px-3 py-2 text-center">
            <p className="font-mono text-correct text-lg">{correctCount}</p>
            <p className="text-muted text-xs">Correct (MCQ)</p>
          </div>
          <div className="bg-bg border border-border rounded-lg px-3 py-2 text-center">
            <p className="font-mono text-incorrect text-lg">{incorrectCount}</p>
            <p className="text-muted text-xs">Incorrect (MCQ)</p>
          </div>
          {theoryCount > 0 && (
            <div className="bg-bg border border-border rounded-lg px-3 py-2 text-center">
              <p className="font-mono text-accent text-lg">{theoryCount}</p>
              <p className="text-muted text-xs">Theory questions</p>
            </div>
          )}
          <div className="bg-bg border border-border rounded-lg px-3 py-2 text-center">
            <p className="font-mono text-ink text-lg">
              {formatClock(timeSpentSeconds)}
            </p>
            <p className="text-muted text-xs">Time spent</p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={onReviewAnswers}
            className="bg-accent text-bg font-semibold rounded-lg py-2.5 hover:opacity-90 transition-opacity"
          >
            Review answers
          </button>
          <div className="flex gap-2">
            <button
              onClick={onRetake}
              className="flex-1 border border-border rounded-lg py-2.5 text-sm hover:border-accent transition-colors"
            >
              Retake quiz
            </button>
            <button
              onClick={handleDownload}
              disabled={downloadingPdf}
              className="flex-1 border border-border rounded-lg py-2.5 text-sm hover:border-accent transition-colors disabled:opacity-50"
            >
              {downloadingPdf ? "Preparing PDF..." : "Download PDF"}
            </button>
          </div>
          <button
            onClick={onClose}
            className="text-muted text-sm hover:text-ink transition-colors mt-1"
          >
            Back to dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportCardModal;
