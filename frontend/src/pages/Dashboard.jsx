import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  BookOpen,
  Brain,
  TrendingUp,
  Trash2,
  Flame,
  Target,
  FileText,
  Zap,
  Crosshair,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api, formatDate, formatDuration, gradeFromPercentage } from "../api";
import Layout from "../components/Layout";
import StatCard from "../components/StatCard";
import Skeleton from "../components/Skeleton";
import UploadPanel from "../components/UploadPanel";
import usePageTitle from "../hooks/usePageTitle";

useEffect(() => {
  if (window.location.hash === "#upload") {
    document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" });
  }
}, []);

const DIFFICULTY_COLORS = {
  easy: "border-correct text-correct",
  hard: "border-accent text-accent",
  difficult: "border-incorrect text-incorrect",
  lecturer_style: "border-muted text-muted",
};

const SOURCE_LABELS = {
  pdf: "PDF",
  docx: "Word",
  text: "Pasted",
  url: "Web page",
  youtube: "YouTube",
  audio: "Audio",
};

function buildInsights(stats, attempts) {
  const insights = [];

  if (!stats || stats.total_quizzes === 0) {
    insights.push(
      "Upload a document and take your first quiz to start building your study profile.",
    );
    return insights;
  }

  if (stats.current_streak >= 2) {
    insights.push(
      `You're on a ${stats.current_streak}-day streak - keep it going!`,
    );
  } else {
    insights.push("Study or take a quiz today to start a new streak.");
  }

  if (stats.average_score >= 80) {
    insights.push(
      `Strong average score (${stats.average_score}%) - try the Difficult tier to push yourself further.`,
    );
  } else if (stats.average_score < 50 && stats.total_quizzes > 0) {
    insights.push(
      `Your average score is ${stats.average_score}% - revisit "Explain my mistakes" on recent quizzes to close gaps.`,
    );
  }

  if (attempts && attempts.length >= 2) {
    const recent = attempts.slice(0, 3);
    const trendUp = recent[0].percentage > recent[recent.length - 1].percentage;
    if (trendUp) {
      insights.push("Your recent scores are trending up - nice work.");
    }
  }

  return insights;
}

const Dashboard = () => {
  usePageTitle("Dashboard");
  const [documents, setDocuments] = useState([]);
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [attempts, setAttempts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [deletingId, setDeletingId] = useState(null);
  const [weakSpotsLoadingId, setWeakSpotsLoadingId] = useState(null);

  const loadAll = async () => {
    try {
      const [docsData, profileData, statsData, attemptsData] =
        await Promise.all([
          api.get("/documents"),
          api.get("/profile").catch(() => null),
          api.get("/profile/stats").catch(() => null),
          api.get("/attempts").catch(() => ({ attempts: [] })),
        ]);
      setDocuments(docsData.documents);
      setProfile(profileData);
      setStats(statsData);
      setAttempts(attemptsData.attempts);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleDelete = async (doc) => {
    toast(
      (t) => (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Delete "{doc.title}"?</p>
          <p className="text-xs text-muted">
            Removes all quizzes, attempts, and history. Can't be undone.
          </p>
          <div className="flex gap-2 mt-1">
            <button
              onClick={() => {
                toast.dismiss(t.id);
                doDelete(doc);
              }}
              className="text-xs bg-incorrect text-bg rounded px-3 py-1.5 font-medium"
            >
              Delete
            </button>
            <button
              onClick={() => toast.dismiss(t.id)}
              className="text-xs border border-border rounded px-3 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      ),
      { duration: 10000 },
    );
  };

  const doDelete = async (doc) => {
    setDeletingId(doc.id);
    try {
      await api.delete(`/documents/${doc.id}`);
      toast.success("Document deleted");
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  // Derive per-document quiz stats from already-loaded attempts, no extra
  // network call needed since attempts are already fetched for the chart.
  const docStats = useMemo(() => {
    if (!attempts) return {};
    return attempts.reduce((acc, a) => {
      if (!a.submitted_at) return acc;
      const id = a.document_id;
      if (!acc[id]) acc[id] = { count: 0, best: 0, last: null };
      acc[id].count += 1;
      if (a.percentage > acc[id].best) acc[id].best = a.percentage;
      if (!acc[id].last || a.submitted_at > acc[id].last)
        acc[id].last = a.submitted_at;
      return acc;
    }, {});
  }, [attempts]);

  const handleUploaded = async () => {
    await loadAll();
  };

  const recentAttempts = (attempts || []).slice(0, 3);
  const chartData = (attempts || [])
    .slice(0, 8)
    .slice()
    .reverse()
    .map((a, i) => ({ name: `#${i + 1}`, percentage: a.percentage }));

  const insights = buildInsights(stats, attempts);

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-1">
          {profile ? `Welcome back, ${profile.username}` : "Welcome back"}
        </h1>
        <p className="text-muted text-sm">
          Upload course material, study it, then test yourself with a generated
          quiz.
        </p>
      </div>

      {/* Stats row */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : (
        stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <StatCard
              label="Day streak"
              value={stats.current_streak}
              icon={<Flame size={16} />}
            />
            <StatCard
              label="Quizzes taken"
              value={stats.total_quizzes}
              icon={<Zap size={16} />}
            />
            <StatCard
              label="Avg. score"
              value={`${stats.average_score}%`}
              icon={<Target size={16} />}
            />
            <StatCard
              label="Documents"
              value={stats.total_documents}
              icon={<FileText size={16} />}
            />
          </div>
        )
      )}

      {/* Insights */}
      {!loading && insights.length > 0 && (
        <div className="bg-accent-soft border border-accent/30 rounded-xl p-4 mb-8 space-y-1.5">
          {insights.map((text, i) => (
            <p key={i} className="text-sm text-ink">
              {text}
            </p>
          ))}
        </div>
      )}

      {/* Progress chart + recent quizzes */}
      {!loading && attempts && attempts.length > 0 && (
        <div className="grid lg:grid-cols-3 gap-4 mb-10">
          <div className="lg:col-span-2 bg-surface border border-border rounded-xl p-5">
            <p className="text-sm text-muted mb-4">Recent quiz scores</p>
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid
                    stroke="rgb(var(--color-border))"
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    dataKey="name"
                    stroke="rgb(var(--color-muted))"
                    fontSize={12}
                  />
                  <YAxis
                    stroke="rgb(var(--color-muted))"
                    fontSize={12}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgb(var(--color-surface))",
                      border: "1px solid rgb(var(--color-border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value) => [`${value}%`, "Score"]}
                  />
                  <Line
                    type="monotone"
                    dataKey="percentage"
                    stroke="rgb(var(--color-accent))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-muted">Recent quizzes</p>
              <Link
                to="/history"
                className="text-xs text-accent hover:underline"
              >
                View all
              </Link>
            </div>
            <div className="space-y-2">
              {recentAttempts.map((a) => (
                <Link
                  key={a.id}
                  to={`/results/${a.id}`}
                  className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-2 hover:border-accent transition-colors"
                >
                  <div className="min-w-0">
                    <p className="truncate">{a.document_title}</p>
                    <p className="text-xs text-muted">
                      {formatDate(a.submitted_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span
                      className={`font-mono text-xs px-1.5 py-0.5 rounded border capitalize ${
                        DIFFICULTY_COLORS[a.difficulty] ||
                        "border-border text-muted"
                      }`}
                    >
                      {a.difficulty[0].toUpperCase()}
                    </span>
                    <span className="font-mono text-xs w-6 h-6 flex items-center justify-center rounded-full border border-accent/30 bg-accent-soft text-accent">
                      {gradeFromPercentage(a.percentage)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Upload */}
      <div id="upload">
        <UploadPanel onUploaded={handleUploaded} />
      </div>

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mb-6">
          {error}
        </p>
      )}

      <h2 className="text-lg font-semibold mb-1">Your course material</h2>
      <p className="text-sm text-muted mb-4">
        Everything you've uploaded. Study it, generate a quiz, track your
        progress, or focus on weak spots.
      </p>

      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-10 text-center">
          <BookOpen size={32} className="text-muted mx-auto mb-3" />
          <p className="font-medium mb-1">No course material yet</p>
          <p className="text-sm text-muted">
            Upload a PDF, paste your notes, or link a YouTube lecture above to
            get started.
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {documents.map((doc) => {
            const ds = docStats[doc.id];
            return (
              <div
                key={doc.id}
                className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-4 transition-transform hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/5"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted border border-border rounded px-1.5 py-0.5">
                      {SOURCE_LABELS[doc.source_type] || doc.source_type}
                    </span>
                  </div>
                  <h3
                    className="font-semibold text-lg leading-snug line-clamp-2"
                    title={doc.title}
                  >
                    {doc.title}
                  </h3>
                  <p className="text-xs text-muted mt-1 font-mono">
                    {doc.page_count} page{doc.page_count === 1 ? "" : "s"} ·{" "}
                    {formatDate(doc.uploaded_at)}
                  </p>
                </div>

                {ds ? (
                  <div className="grid grid-cols-3 gap-2 text-center border border-border rounded-lg p-2">
                    <div>
                      <p className="text-lg font-semibold">{ds.count}</p>
                      <p className="text-[10px] text-muted uppercase tracking-wide font-mono">
                        Quizzes
                      </p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-accent">
                        {ds.best}%
                      </p>
                      <p className="text-[10px] text-muted uppercase tracking-wide font-mono">
                        Best
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium mt-1">
                        {formatDate(ds.last)}
                      </p>
                      <p className="text-[10px] text-muted uppercase tracking-wide font-mono">
                        Last quiz
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center border border-dashed border-border rounded-lg py-3">
                    <p className="text-xs text-muted">No quizzes yet</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 mt-auto">
                  <Link
                    to={`/documents/${doc.id}/study`}
                    className="flex items-center justify-center gap-1.5 text-sm border border-border rounded-lg px-3 py-1.5 hover:border-accent transition-colors"
                  >
                    <BookOpen size={13} /> Study
                  </Link>
                  <Link
                    to={`/documents/${doc.id}/quiz-setup`}
                    className="flex items-center justify-center gap-1.5 text-sm bg-accent text-bg font-medium rounded-lg px-3 py-1.5 hover:opacity-90 transition-opacity"
                  >
                    <Brain size={13} /> Take quiz
                  </Link>
                  <Link
                    to={`/documents/${doc.id}/performance`}
                    className="flex items-center justify-center gap-1.5 text-sm border border-border rounded-lg px-3 py-1.5 hover:border-accent transition-colors"
                  >
                    <TrendingUp size={13} /> Progress
                  </Link>
                  <button
                    onClick={async () => {
                      setWeakSpotsLoadingId(doc.id);
                      try {
                        const quiz = await api.post(
                          `/documents/${doc.id}/weak-spots-quiz`,
                        );
                        window.location.href = `/quiz/${quiz.id}`;
                      } catch (err) {
                        toast(err.message, { icon: "🎯" });
                        setWeakSpotsLoadingId(null);
                      }
                    }}
                    disabled={weakSpotsLoadingId === doc.id}
                    className="flex items-center justify-center gap-1.5 text-sm border border-border rounded-lg px-3 py-1.5 hover:border-accent transition-colors disabled:opacity-50"
                    title="Generate a quiz targeting your weakest topics on this document"
                  >
                    <Crosshair size={13} />
                    {weakSpotsLoadingId === doc.id
                      ? "Generating..."
                      : "Weak spots"}
                  </button>
                </div>
                <button
                  onClick={() => handleDelete(doc)}
                  disabled={deletingId === doc.id}
                  className="flex items-center justify-center gap-1.5 text-xs text-incorrect hover:text-incorrect/80 transition-colors disabled:opacity-50"
                >
                  <Trash2 size={12} />
                  {deletingId === doc.id ? "Deleting..." : "Delete document"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </Layout>
  );
};

export default Dashboard;
