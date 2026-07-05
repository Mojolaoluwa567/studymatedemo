import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  BookOpen, FileText, Lightbulb, LayoutGrid, Sparkles, Download, Target,
  Timer, Play, Pause, CheckCircle,
} from "lucide-react";
import { api, API_URL } from "../api";
import Layout from "../components/Layout";
import { SkeletonLines, SkeletonCards } from "../components/Skeleton";
import Flashcards from "../components/Flashcards";
import BackButton from "../components/BackButton";
function formatClock(seconds) {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

const TABS = [
  { key: "read", label: "Read", icon: <BookOpen size={14} /> },
  { key: "summary", label: "Summary", icon: <FileText size={14} /> },
  { key: "concepts", label: "Key Concepts", icon: <Lightbulb size={14} /> },
  { key: "flashcards", label: "Flashcards", icon: <LayoutGrid size={14} /> },
  { key: "explainer", label: "Explainer", icon: <Sparkles size={14} /> },
  { key: "mastery", label: "Mastery", icon: <Target size={14} /> },
];

const StudySession = () => {
  const { id } = useParams();
  const [document_, setDocument] = useState(null);
  const [error, setError] = useState("");

  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [logged, setLogged] = useState(null);
  const intervalRef = useRef(null);

  const [tab, setTab] = useState("read");
  const [summary, setSummary] = useState(null);
  const [concepts, setConcepts] = useState(null);
  const [flashcards, setFlashcards] = useState(null);
  const [explainerHtml, setExplainerHtml] = useState(null);
  const [mastery, setMastery] = useState(null);
  const [downloadingGuide, setDownloadingGuide] = useState(false);
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState("");

  useEffect(() => {
    api
      .get(`/documents/${id}`)
      .then(setDocument)
      .catch((err) => setError(err.message));
  }, [id]);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  const handleLogSession = async () => {
    if (elapsed < 1) return;
    setRunning(false);
    try {
      const data = await api.post("/study-sessions", {
        document_id: Number(id),
        duration_seconds: elapsed,
      });
      setLogged(data.total_study_seconds);
      setElapsed(0);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTabChange = async (key) => {
    setTab(key);
    setTabError("");

    if (key === "summary" && summary === null) {
      setTabLoading(true);
      try {
        const data = await api.get(`/documents/${id}/summary`);
        setSummary(data.summary);
      } catch (err) {
        setTabError(err.message);
        toast.error(err.message);
      } finally {
        setTabLoading(false);
      }
    } else if (key === "concepts" && concepts === null) {
      setTabLoading(true);
      try {
        const data = await api.get(`/documents/${id}/key-concepts`);
        setConcepts(data.key_concepts);
      } catch (err) {
        setTabError(err.message);
        toast.error(err.message);
      } finally {
        setTabLoading(false);
      }
    } else if (key === "flashcards" && flashcards === null) {
      setTabLoading(true);
      try {
        const data = await api.get(`/documents/${id}/flashcards`);
        setFlashcards(data.flashcards);
      } catch (err) {
        setTabError(err.message);
        toast.error(err.message);
      } finally {
        setTabLoading(false);
      }
    } else if (key === "explainer" && explainerHtml === null) {
      setTabLoading(true);
      try {
        const data = await api.get(`/documents/${id}/explainer`);
        setExplainerHtml(data.explainer_html);
      } catch (err) {
        setTabError(err.message);
        toast.error(err.message);
      } finally {
        setTabLoading(false);
      }
    } else if (key === "mastery" && mastery === null) {
      setTabLoading(true);
      try {
        const data = await api.get(`/documents/${id}/mastery`);
        setMastery(data.topics);
      } catch (err) {
        setTabError(err.message);
      } finally {
        setTabLoading(false);
      }
    }
  };

  const handleDownloadStudyGuide = async () => {
    setDownloadingGuide(true);
    try {
      const response = await fetch(`${API_URL}/documents/${id}/export-study-guide`, {
        credentials: "include",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          body.error || "Generate a study aid first (Summary, Key Concepts, or Flashcards), then try downloading again."
        );
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${document_?.title || "study_guide"}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDownloadingGuide(false);
    }
  };

  if (error) {
    return (
      <Layout>
        <BackButton />
        <p className="text-incorrect">{error}</p>
      </Layout>
    );
  }

  if (!document_) {
    return (
      <Layout>
        <BackButton />
        <p className="text-muted text-sm">Loading...</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <BackButton />
      <div className="mb-6 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold">{document_.title}</h1>
          <p className="text-muted text-sm">
            {document_.page_count} page{document_.page_count === 1 ? "" : "s"}
          </p>
          <button
            onClick={handleDownloadStudyGuide}
            disabled={downloadingGuide}
            className="flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors mt-1 disabled:opacity-50"
          >
            <Download size={12} />
            {downloadingGuide ? "Preparing PDF..." : "Download study guide PDF"}
          </button>
        </div>

        <div className="flex items-center gap-3 bg-surface border border-border rounded-xl px-4 py-3">
          <Timer size={18} className="text-muted shrink-0" />
          <span className="font-mono text-2xl tabular-nums">
            {formatClock(elapsed)}
          </span>
          {!running ? (
            <button
              onClick={() => setRunning(true)}
              className="flex items-center gap-1.5 bg-accent text-bg font-semibold rounded-lg px-4 py-1.5 text-sm hover:opacity-90 transition-opacity"
            >
              <Play size={13} />
              {elapsed > 0 ? "Resume" : "Start studying"}
            </button>
          ) : (
            <button
              onClick={() => setRunning(false)}
              className="flex items-center gap-1.5 border border-border rounded-lg px-4 py-1.5 text-sm hover:border-accent transition-colors"
            >
              <Pause size={13} /> Pause
            </button>
          )}
          <button
            onClick={handleLogSession}
            disabled={elapsed < 1}
            className="flex items-center gap-1.5 border border-border rounded-lg px-4 py-1.5 text-sm hover:border-accent transition-colors disabled:opacity-40"
          >
            <CheckCircle size={13} /> Log session
          </button>
        </div>
      </div>

      {logged !== null && (
        <p className="text-correct text-sm border border-correct/30 bg-correct/10 rounded-lg px-3 py-2 mb-6">
          Session logged. Total study time on this document:{" "}
          {Math.floor(logged / 60)}m {logged % 60}s.{" "}
          <Link
            to={`/documents/${id}/quiz-setup`}
            className="underline hover:text-correct"
          >
            Ready to take a quiz?
          </Link>
        </p>
      )}

      <div className="flex gap-2 mb-4 border-b border-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => handleTabChange(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === "read" && (
        document_.has_pdf ? (
          <div className="bg-surface border border-border rounded-xl overflow-hidden" style={{ height: "75vh" }}>
            <iframe
              src={`${API_URL}/documents/${id}/file`}
              title={document_.title}
              className="w-full h-full"
              style={{ border: "none" }}
            />
          </div>
        ) : (
          <div className="bg-surface border border-border rounded-xl p-6 max-h-[65vh] overflow-y-auto whitespace-pre-wrap leading-relaxed text-sm">
            {document_.text_content}
          </div>
        )
      )}

      {tab === "summary" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          {tabLoading ? (
            <SkeletonLines lines={6} />
          ) : tabError ? (
            <p className="text-incorrect text-sm">{tabError}</p>
          ) : (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {summary}
            </p>
          )}
        </div>
      )}

      {tab === "concepts" && (
        <div>
          {tabLoading ? (
            <SkeletonCards count={6} />
          ) : tabError ? (
            <p className="text-incorrect text-sm">{tabError}</p>
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {concepts?.map((c, i) => (
                <div
                  key={i}
                  className="bg-surface border border-border rounded-xl p-4"
                >
                  <p className="font-semibold text-accent mb-1">{c.term}</p>
                  <p className="text-sm text-muted leading-relaxed">
                    {c.explanation}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "flashcards" && (
        <div className="bg-surface border border-border rounded-xl p-6">
          {tabLoading ? (
            <SkeletonLines lines={4} />
          ) : tabError ? (
            <p className="text-incorrect text-sm">{tabError}</p>
          ) : (
            <Flashcards cards={flashcards} />
          )}
        </div>
      )}

      {tab === "explainer" && (
        <div>
          {tabLoading ? (
            <div className="bg-surface border border-border rounded-xl p-10 text-center">
              <p className="text-muted text-sm mb-1">
                Generating your interactive explainer...
              </p>
              <p className="text-xs text-muted">
                This takes a little longer than the other study aids — it's
                building a full interactive page from your material.
              </p>
            </div>
          ) : tabError ? (
            <div className="bg-surface border border-border rounded-xl p-6 text-center">
              <p className="text-incorrect text-sm mb-3">{tabError}</p>
              <button
                onClick={() => {
                  setTabError("");
                  setExplainerHtml(null);
                  handleTabChange("explainer");
                }}
                className="text-sm border border-border rounded-lg px-4 py-2 hover:border-accent transition-colors"
              >
                Try again
              </button>
            </div>
          ) : explainerHtml ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs text-muted font-mono">
                  Interactive explainer — generated from your material
                </p>
                <button
                  onClick={async () => {
                    setExplainerHtml(null);
                    setTabLoading(true);
                    setTabError("");
                    try {
                      const data = await api.get(
                        `/documents/${id}/explainer?force=1`
                      );
                      setExplainerHtml(data.explainer_html);
                    } catch (err) {
                      setTabError(err.message);
                    } finally {
                      setTabLoading(false);
                    }
                  }}
                  className="text-xs text-muted hover:text-ink transition-colors"
                >
                  Regenerate
                </button>
              </div>
              <iframe
                srcDoc={explainerHtml}
                sandbox="allow-scripts"
                className="w-full rounded-xl border border-border"
                style={{ height: "70vh", minHeight: "500px" }}
                title="Interactive explainer"
              />
            </div>
          ) : null}
        </div>
      )}

      {tab === "mastery" && (
        <div>
          {tabLoading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-10 bg-surface border border-border rounded-lg animate-pulse" />)}
            </div>
          ) : !mastery || mastery.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-border rounded-xl">
              <Target size={28} className="text-muted mx-auto mb-3" />
              <p className="text-muted text-sm mb-1">No mastery data yet.</p>
              <p className="text-xs text-muted">Take a few quizzes on this document first.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-muted font-mono mb-4">
                Based on all your quiz attempts on this document. Sorted weakest first.
              </p>
              {mastery.map((t) => {
                const pct = t.mastery_percentage;
                const color = pct >= 70 ? "bg-correct" : pct >= 40 ? "bg-accent" : "bg-incorrect";
                return (
                  <div key={t.topic} className="bg-surface border border-border rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium">{t.topic}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted font-mono">{t.questions_seen} questions</span>
                        <span className={`font-mono text-sm font-semibold ${pct >= 70 ? "text-correct" : pct >= 40 ? "text-accent" : "text-incorrect"}`}>
                          {pct}%
                        </span>
                      </div>
                    </div>
                    <div className="h-2 bg-border rounded-full overflow-hidden">
                      <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </Layout>
  );
};

export default StudySession;
