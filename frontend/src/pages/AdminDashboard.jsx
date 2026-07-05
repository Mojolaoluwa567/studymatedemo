import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Users, FileText, Zap, BarChart2, Trash2, ChevronRight } from "lucide-react";
import { api, formatDate, difficultyLabel } from "../api";
import Layout from "../components/Layout";
import StatCard from "../components/StatCard";
import Skeleton from "../components/Skeleton";
import BackButton from "../components/BackButton";
import usePageTitle from "../hooks/usePageTitle";

const SOURCE_LABELS = {
  pdf: "PDF",
  docx: "Word",
  text: "Pasted",
  url: "Web page",
  youtube: "YouTube",
  audio: "Audio",
};

const TABS = [
  { key: "users", label: "Users" },
  { key: "content", label: "Content" },
  { key: "usage", label: "Usage" },
];

const UserDetailPanel = ({ userId, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/admin/users/${userId}`)
      .then(setDetail)
      .catch((err) => setError(err.message));
  }, [userId]);

  if (error) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <p className="text-incorrect text-sm">{error}</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold">{detail.username}</h3>
          <p className="text-xs text-muted">{detail.email}</p>
        </div>
        <button
          onClick={onClose}
          className="text-sm text-muted hover:text-ink transition-colors"
        >
          Close
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <StatCard label="Role" value={detail.role} />
        <StatCard
          label="Avg. score"
          value={detail.average_score !== null ? `${detail.average_score}%` : "—"}
        />
        <StatCard label="Joined" value={formatDate(detail.created_at)} />
      </div>

      <p className="text-xs text-muted uppercase tracking-wide mb-2 font-mono">
        Documents ({detail.documents.length})
      </p>
      <div className="space-y-1.5 mb-5">
        {detail.documents.length === 0 ? (
          <p className="text-sm text-muted">None uploaded.</p>
        ) : (
          detail.documents.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-1.5"
            >
              <span>{d.title}</span>
              <span className="text-xs text-muted font-mono">
                {SOURCE_LABELS[d.source_type] || d.source_type}
              </span>
            </div>
          ))
        )}
      </div>

      <p className="text-xs text-muted uppercase tracking-wide mb-2 font-mono">
        Recent attempts ({detail.recent_attempts.length})
      </p>
      <div className="space-y-1.5">
        {detail.recent_attempts.length === 0 ? (
          <p className="text-sm text-muted">None yet.</p>
        ) : (
          detail.recent_attempts.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-1.5"
            >
              <span>{difficultyLabel(a.difficulty)}</span>
              <span className="font-mono text-xs text-accent">
                {a.percentage}%
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const AdminDashboard = () => {
  usePageTitle("Admin");
  const [overview, setOverview] = useState(null);
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState(null);
  const [content, setContent] = useState(null);
  const [usage, setUsage] = useState(null);
  const [search, setSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/overview").then(setOverview).catch((err) => setError(err.message));
  }, []);

  const loadUsers = (searchValue = "") => {
    const q = searchValue ? `?search=${encodeURIComponent(searchValue)}` : "";
    api.get(`/admin/users${q}`).then((data) => setUsers(data.users)).catch(() => {});
  };

  const loadContent = (searchValue = "") => {
    const q = searchValue ? `?search=${encodeURIComponent(searchValue)}` : "";
    api.get(`/admin/content${q}`).then((data) => setContent(data.documents)).catch(() => {});
  };

  useEffect(() => {
    if (tab === "users" && users === null) loadUsers();
    if (tab === "content" && content === null) loadContent();
    if (tab === "usage" && usage === null) {
      api.get("/admin/usage").then(setUsage).catch(() => {});
    }
  }, [tab]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (tab === "users") loadUsers(search);
    if (tab === "content") loadContent(search);
  };

  const handleDeleteContent = async (doc) => {
    toast((t) => (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">Delete "{doc.title}"?</p>
        <p className="text-xs text-muted">
          Uploaded by {doc.owner_username}. Cascades to all quizzes and
          attempts. Can't be undone.
        </p>
        <div className="flex gap-2 mt-1">
          <button
            onClick={() => { toast.dismiss(t.id); doDeleteContent(doc); }}
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
    ), { duration: 10000 });
  };

  const doDeleteContent = async (doc) => {
    try {
      await api.delete(`/admin/content/${doc.id}`);
      toast.success("Document deleted");
      setContent((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (error) {
    return (
      <Layout>
        <BackButton />
        <p className="text-incorrect text-sm">{error}</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1">Admin</h1>
      <p className="text-muted text-sm mb-8">
        Platform-wide oversight - users, content, and usage.
      </p>

      {!overview ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard label="Total users" value={overview.total_users} icon={<Users size={16} />} />
          <StatCard label="Documents" value={overview.total_documents} icon={<FileText size={16} />} />
          <StatCard label="Quizzes generated" value={overview.total_quizzes} icon={<Zap size={16} />} />
          <StatCard
            label="Platform avg. score"
            value={
              overview.platform_average_score !== null
                ? `${overview.platform_average_score}%`
                : "—"
            }
            icon={<BarChart2 size={16} />}
          />
        </div>
      )}

      {overview && (
        <div className="flex flex-wrap gap-4 text-xs text-muted font-mono mb-8">
          <span>{overview.total_students} students</span>
          <span>·</span>
          <span>{overview.total_teachers} teachers</span>
          <span>·</span>
          <span>{overview.new_users_7d} new this week</span>
          <span>·</span>
          <span>{overview.active_users_7d} active this week</span>
        </div>
      )}

      <div className="flex gap-2 mb-4 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => {
              setTab(t.key);
              setSearch("");
              setSelectedUserId(null);
            }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {(tab === "users" || tab === "content") && (
        <form onSubmit={handleSearch} className="flex gap-2 mb-5">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={tab === "users" ? "Search username or email..." : "Search document title..."}
            className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
          />
          <button
            type="submit"
            className="border border-border rounded-lg px-4 py-2 text-sm hover:border-accent transition-colors"
          >
            Search
          </button>
        </form>
      )}

      {tab === "users" && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div>
            {users === null ? (
              <div className="space-y-2">
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </div>
            ) : users.length === 0 ? (
              <p className="text-sm text-muted">No users found.</p>
            ) : (
              <div className="space-y-2">
                {users.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => setSelectedUserId(u.id)}
                    className={`w-full text-left flex items-center justify-between text-sm border rounded-lg px-3 py-2.5 transition-colors ${
                      selectedUserId === u.id
                        ? "border-accent bg-accent-soft"
                        : "border-border hover:border-accent/50"
                    }`}
                  >
                    <div>
                      <p className="font-medium">
                        {u.username}
                        {u.is_admin && (
                          <span className="ml-2 text-xs font-mono text-accent">
                            admin
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-muted">{u.email}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted capitalize">{u.role}</p>
                      <p className="text-xs font-mono text-muted">
                        {u.document_count} docs · {u.quiz_attempt_count} quizzes
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            {selectedUserId ? (
              <UserDetailPanel
                userId={selectedUserId}
                onClose={() => setSelectedUserId(null)}
              />
            ) : (
              <div className="text-center py-12 border border-dashed border-border rounded-xl">
                <p className="text-muted text-sm">
                  Select a user to see their activity.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "content" && (
        <div className="space-y-2">
          {content === null ? (
            <>
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </>
          ) : content.length === 0 ? (
            <p className="text-sm text-muted">No documents found.</p>
          ) : (
            content.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between text-sm border border-border rounded-lg px-4 py-3"
              >
                <div>
                  <p className="font-medium">{d.title}</p>
                  <p className="text-xs text-muted">
                    {SOURCE_LABELS[d.source_type] || d.source_type} ·{" "}
                    {d.page_count} page{d.page_count === 1 ? "" : "s"} · uploaded
                    by {d.owner_username} · {formatDate(d.uploaded_at)}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteContent(d)}
                  className="flex items-center gap-1 text-xs text-incorrect hover:underline shrink-0 ml-3"
                >
                  <Trash2 size={12} /> Delete
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "usage" && (
        <div>
          {usage === null ? (
            <Skeleton className="h-64" />
          ) : (
            <div className="space-y-6">
              <div>
                <p className="text-sm text-muted mb-3">
                  Estimated AI calls:{" "}
                  <span className="font-mono text-accent text-base">
                    {usage.estimated_total_ai_calls}
                  </span>{" "}
                  <span className="text-xs">
                    (derived from generated content, not metered from Gemini
                    directly - see README)
                  </span>
                </p>
                <div className="grid sm:grid-cols-3 gap-3">
                  <StatCard
                    label="Quiz generations"
                    value={usage.breakdown.quiz_generations}
                  />
                  <StatCard
                    label="Theory grading batches"
                    value={usage.breakdown.theory_grading_batches}
                  />
                  <StatCard
                    label="Explanations"
                    value={usage.breakdown.explanations_generated}
                  />
                  <StatCard
                    label="Summaries"
                    value={usage.breakdown.summaries_generated}
                  />
                  <StatCard
                    label="Key concepts"
                    value={usage.breakdown.key_concepts_generated}
                  />
                  <StatCard
                    label="Flashcards"
                    value={usage.breakdown.flashcards_generated}
                  />
                </div>
              </div>

              <div>
                <p className="text-sm text-muted mb-3">Average score by difficulty</p>
                <div className="space-y-2">
                  {usage.score_by_difficulty.length === 0 ? (
                    <p className="text-sm text-muted">No attempts yet.</p>
                  ) : (
                    usage.score_by_difficulty.map((row) => (
                      <div
                        key={row.difficulty}
                        className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-2"
                      >
                        <span>{difficultyLabel(row.difficulty)}</span>
                        <span className="font-mono text-xs text-muted">
                          {row.attempt_count} attempts ·{" "}
                          {row.average_percentage}% avg
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Layout>
  );
};

export default AdminDashboard;
