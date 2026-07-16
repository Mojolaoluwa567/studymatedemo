import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Copy,
  BarChart2,
  Users,
  Users2,
  Pencil,
  Trash2,
  CheckCircle2,
  FileEdit,
  Upload,
} from "lucide-react";
import { api, formatDate, gradeFromPercentage } from "../api";
import Layout from "../components/Layout";
import UploadPanel from "../components/UploadPanel";
import StatCard from "../components/StatCard";
import Skeleton from "../components/Skeleton";
import usePageTitle from "../hooks/usePageTitle";

const DIFFICULTY_OPTIONS = [
  { value: "easy", label: "Easy" },
  { value: "hard", label: "Hard" },
  { value: "difficult", label: "Difficult" },
];

const CreateAssignmentForm = ({ documents, onDraftCreated }) => {
  const [documentId, setDocumentId] = useState("");
  const [difficulty, setDifficulty] = useState("easy");
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!documentId) {
      setError("Choose a document first.");
      return;
    }
    setError("");
    setCreating(true);
    try {
      const draft = await api.post("/assignments", {
        document_id: Number(documentId),
        difficulty,
        title: title || undefined,
      });
      toast.success("Questions generated - review before publishing");
      setTitle("");
      setDocumentId("");
      onDraftCreated(draft.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted">
        Upload a document below first, then come back here to turn it into an
        assignment.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-sm text-muted mb-1">Document</label>
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
          >
            <option value="">Choose...</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-muted mb-1">Difficulty</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
          >
            {DIFFICULTY_OPTIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-muted mb-1">
            Assignment name (optional)
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Week 1 Quiz"
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
          />
        </div>
      </div>

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={creating}
        className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {creating ? "Generating quiz..." : "Generate questions"}
      </button>
    </form>
  );
};

const EditQuestionForm = ({ question, onSave, onCancel }) => {
  const [text, setText] = useState(question.question);
  const [marks, setMarks] = useState(question.marks);
  const [options, setOptions] = useState(question.options || {});
  const [correctAnswer, setCorrectAnswer] = useState(question.correct_answer);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        question_text: text,
        marks: Number(marks),
        correct_answer: correctAnswer,
      };
      if (question.type === "mcq") payload.options = options;
      await onSave(question.id, payload);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={2}
        className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors resize-y"
      />

      {question.type === "mcq" ? (
        <div className="space-y-2">
          {Object.entries(options).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCorrectAnswer(key)}
                className={`w-7 h-7 shrink-0 rounded-full border text-xs font-mono flex items-center justify-center transition-colors ${
                  correctAnswer === key
                    ? "border-correct bg-correct/10 text-correct"
                    : "border-border text-muted hover:border-accent"
                }`}
                title="Mark as correct answer"
              >
                {key}
              </button>
              <input
                value={value}
                onChange={(e) =>
                  setOptions((prev) => ({ ...prev, [key]: e.target.value }))
                }
                className="flex-1 bg-bg border border-border rounded-lg px-3 py-1.5 text-sm outline-none focus:border-accent transition-colors"
              />
            </div>
          ))}
          <p className="text-xs text-muted">
            Click a letter to mark it as the correct answer.
          </p>
        </div>
      ) : (
        <div>
          <label className="block text-xs text-muted mb-1">
            Model answer / marking points
          </label>
          <textarea
            value={correctAnswer}
            onChange={(e) => setCorrectAnswer(e.target.value)}
            rows={3}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors resize-y"
          />
        </div>
      )}

      <div className="flex items-center gap-3">
        <label className="text-xs text-muted">Marks</label>
        <input
          type="number"
          min={1}
          value={marks}
          onChange={(e) => setMarks(e.target.value)}
          className="w-20 bg-bg border border-border rounded-lg px-2 py-1 text-sm outline-none focus:border-accent transition-colors"
        />
        <div className="ml-auto flex gap-2">
          <button
            onClick={onCancel}
            className="text-sm border border-border rounded-lg px-3 py-1.5 hover:border-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-sm bg-accent text-bg font-medium rounded-lg px-3 py-1.5 hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
};

const ReviewDraftPanel = ({ draftId, onPublished, onClose }) => {
  const [quiz, setQuiz] = useState(null);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [publishing, setPublishing] = useState(false);

  const load = () => {
    api
      .get(`/assignments/${draftId}/questions`)
      .then(setQuiz)
      .catch((err) => setError(err.message));
  };

  useEffect(load, [draftId]);

  const handleSaveEdit = async (questionId, payload) => {
    try {
      const updated = await api.patch(
        `/assignments/${draftId}/questions/${questionId}`,
        payload,
      );
      setQuiz(updated);
      setEditingId(null);
      toast.success("Question updated");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (questionId) => {
    try {
      const updated = await api.delete(
        `/assignments/${draftId}/questions/${questionId}`,
      );
      setQuiz(updated);
      toast.success("Question removed");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      const published = await api.post(`/assignments/${draftId}/publish`);
      toast.success(`Published! Join code: ${published.join_code}`);
      onPublished();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setPublishing(false);
    }
  };

  if (error) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <p className="text-incorrect text-sm">{error}</p>
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="bg-surface border border-accent/40 rounded-xl p-5">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div>
          <p className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wide text-accent mb-1">
            <FileEdit size={12} /> Draft - review before publishing
          </p>
          <h3 className="font-semibold">{quiz.title}</h3>
        </div>
        <button
          onClick={onClose}
          className="text-sm text-muted hover:text-ink transition-colors"
        >
          Close
        </button>
      </div>
      <p className="text-xs text-muted font-mono mb-4">
        {quiz.num_questions} questions · {quiz.total_marks} marks
      </p>

      <div className="space-y-3 mb-5 max-h-[50vh] overflow-y-auto pr-1">
        {quiz.questions.length === 0 ? (
          <p className="text-sm text-incorrect">
            No questions left - delete fewer, or generate a new draft.
          </p>
        ) : (
          quiz.questions.map((q, idx) => (
            <div key={q.id} className="border border-border rounded-lg p-3">
              {editingId === q.id ? (
                <EditQuestionForm
                  question={q}
                  onSave={handleSaveEdit}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p className="text-sm font-medium leading-relaxed">
                      <span className="font-mono text-accent mr-1.5">
                        {idx + 1}.
                      </span>
                      {q.question}
                    </p>
                    <span className="font-mono text-xs text-muted border border-border rounded px-1.5 py-0.5 shrink-0">
                      {q.marks} mark{q.marks === 1 ? "" : "s"}
                    </span>
                  </div>
                  {q.type === "mcq" && q.options && (
                    <div className="text-xs text-muted space-y-0.5 mb-2 ml-5">
                      {Object.entries(q.options).map(([key, value]) => (
                        <p
                          key={key}
                          className={
                            key === q.correct_answer
                              ? "text-correct font-medium"
                              : ""
                          }
                        >
                          {key}. {value} {key === q.correct_answer && "✓"}
                        </p>
                      ))}
                    </div>
                  )}
                  {q.type === "theory" && (
                    <p className="text-xs text-muted mb-2 ml-5">
                      Model answer: {q.correct_answer}
                    </p>
                  )}
                  <div className="flex gap-2 ml-5">
                    <button
                      onClick={() => setEditingId(q.id)}
                      className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
                    >
                      <Pencil size={12} /> Edit
                    </button>
                    <button
                      onClick={() => handleDelete(q.id)}
                      className="flex items-center gap-1 text-xs text-muted hover:text-incorrect transition-colors"
                    >
                      <Trash2 size={12} /> Remove
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      <button
        onClick={handlePublish}
        disabled={publishing || quiz.questions.length === 0}
        className="w-full flex items-center justify-center gap-2 bg-accent text-bg font-semibold rounded-lg py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        <CheckCircle2 size={16} />
        {publishing ? "Publishing..." : "Publish assignment"}
      </button>
    </div>
  );
};

const AssignmentCard = ({ assignment, onViewResults, onReview, selected }) => {
  const handleCopyCode = () => {
    navigator.clipboard?.writeText(assignment.join_code);
    toast.success("Join code copied");
  };

  return (
    <div
      className={`bg-surface border rounded-xl p-5 transition-colors ${selected ? "border-accent" : "border-border"}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold leading-snug">{assignment.title}</h3>
            {!assignment.is_published && (
              <span className="text-[10px] font-mono uppercase tracking-wide text-accent border border-accent/40 rounded-full px-2 py-0.5">
                Draft
              </span>
            )}
          </div>
          <p className="text-xs text-muted mt-1 font-mono capitalize">
            {assignment.difficulty} · {assignment.num_questions} questions ·{" "}
            {assignment.total_marks} marks
          </p>
        </div>
        <span className="text-xs text-muted font-mono whitespace-nowrap">
          {formatDate(assignment.created_at)}
        </span>
      </div>

      {assignment.is_published ? (
        <button
          onClick={handleCopyCode}
          className="flex items-center justify-center gap-2 font-mono text-lg tracking-wider bg-accent-soft border border-accent/30 text-accent rounded-lg px-4 py-2 hover:opacity-90 transition-opacity w-full mb-3"
          title="Click to copy"
        >
          <Copy size={14} />
          {assignment.join_code}
        </button>
      ) : (
        <button
          onClick={() => onReview(assignment.id)}
          className="flex items-center justify-center gap-2 text-sm border border-accent/40 text-accent rounded-lg px-4 py-2 hover:bg-accent-soft transition-colors w-full mb-3"
        >
          <FileEdit size={14} /> Review and publish
        </button>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted flex items-center gap-1">
          <Users size={12} />
          {assignment.submitted_attempt_count} submission
          {assignment.submitted_attempt_count === 1 ? "" : "s"}
        </p>
        {assignment.is_published && (
          <button
            onClick={() => onViewResults(assignment.id)}
            className="flex items-center gap-1.5 text-sm text-accent hover:underline"
          >
            <BarChart2 size={14} /> View results
          </button>
        )}
      </div>
    </div>
  );
};

const ResultsPanel = ({ assignmentId, onClose }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/assignments/${assignmentId}/results`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [assignmentId]);

  if (error) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <p className="text-incorrect text-sm">{error}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5">
        <Skeleton className="h-32" />
      </div>
    );
  }

  const avg =
    data.results.length > 0
      ? Math.round(
          (data.results.reduce((sum, r) => sum + r.percentage, 0) /
            data.results.length) *
            10,
        ) / 10
      : 0;

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">{data.assignment.title} — results</h3>
        <button
          onClick={onClose}
          className="text-sm text-muted hover:text-ink transition-colors"
        >
          Close
        </button>
      </div>

      {data.results.length === 0 ? (
        <p className="text-sm text-muted">
          No submissions yet. Share the join code{" "}
          <span className="font-mono text-accent">
            {data.assignment.join_code}
          </span>{" "}
          with students.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <StatCard label="Submissions" value={data.results.length} />
            <StatCard label="Average score" value={`${avg}%`} />
          </div>
          <div className="space-y-2">
            {data.results.map((r) => (
              <div
                key={r.attempt_id}
                className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-2"
              >
                <div>
                  <p className="font-medium">{r.student_username}</p>
                  <p className="text-xs text-muted flex items-center gap-2">
                    {formatDate(r.submitted_at)}
                    {r.tab_switch_count > 0 && (
                      <span
                        className="text-accent"
                        title="Number of times this student's tab lost focus during the attempt - not proof of anything, just a data point."
                      >
                        · left tab {r.tab_switch_count}×
                      </span>
                    )}
                    {r.copy_attempt_count > 0 && (
                      <span
                        className="text-accent"
                        title="Number of copy/cut actions detected on the question content during the attempt - not proof of anything, just a data point."
                      >
                        · copy {r.copy_attempt_count}×
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted">
                    {r.total_score}/{r.max_score}
                  </span>
                  <span className="font-mono text-xs w-7 h-7 flex items-center justify-center rounded-full border border-accent/30 bg-accent-soft text-accent">
                    {gradeFromPercentage(r.percentage)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

const BulkUploadPanel = ({ onUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);

  const handleChange = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true);
    setResults(null);
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    try {
      const data = await api.upload("/documents/bulk", form);
      setResults(data.results);
      toast.success(`${data.succeeded} uploaded, ${data.failed} failed`);
      if (data.succeeded > 0) onUploaded();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <div>
      <label
        className={`flex items-center gap-2 border border-dashed border-border rounded-lg px-4 py-3 cursor-pointer hover:border-accent transition-colors ${uploading ? "opacity-50 pointer-events-none" : ""}`}
      >
        <Upload size={16} className="text-muted" />
        <span className="text-sm text-muted">
          {uploading
            ? "Uploading..."
            : "Click to choose multiple PDFs or Word docs"}
        </span>
        <input
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.docx"
          onChange={handleChange}
        />
      </label>
      {results && (
        <div className="mt-3 space-y-1">
          {results.map((r, i) => (
            <p
              key={i}
              className={`text-xs font-mono ${r.success ? "text-correct" : "text-incorrect"}`}
            >
              {r.success ? "✓" : "✗"} {r.filename}
              {r.error ? ` — ${r.error}` : ""}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

const ClassesSummaryCard = () => {
  const [classes, setClasses] = useState(null);

  useEffect(() => {
    api
      .get("/classes")
      .then((d) => setClasses(d.classes))
      .catch(() => setClasses([]));
  }, []);

  return (
    <div className="bg-surface border border-border rounded-xl p-5 mb-8">
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-semibold flex items-center gap-2">
          <Users2 size={16} className="text-accent" /> Classes
        </h2>
        <Link to="/classes" className="text-sm text-accent hover:underline">
          Manage classes →
        </Link>
      </div>
      <p className="text-xs text-muted mb-3">
        Group students so every assignment you publish is instantly visible to
        everyone in the class.
      </p>
      {classes === null ? (
        <p className="text-sm text-muted">Loading...</p>
      ) : classes.length === 0 ? (
        <p className="text-sm text-muted">
          No classes yet — create one from the Classes page.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {classes.map((c) => (
            <span
              key={c.id}
              className="text-xs font-mono border border-border rounded-full px-3 py-1"
            >
              {c.name} · {c.member_count} member
              {c.member_count === 1 ? "" : "s"}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const TeacherDashboard = () => {
  usePageTitle("Teacher Dashboard");
  const [profile, setProfile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [viewingResultsFor, setViewingResultsFor] = useState(null);
  const [reviewingDraftId, setReviewingDraftId] = useState(null);
  const [deletingDocId, setDeletingDocId] = useState(null);

  const loadAll = async () => {
    try {
      const [profileData, docsData, assignmentsData] = await Promise.all([
        api.get("/profile").catch(() => null),
        api.get("/documents"),
        api.get("/assignments"),
      ]);
      setProfile(profileData);
      setDocuments(docsData.documents);
      setAssignments(assignmentsData.assignments);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleDraftCreated = (draftId) => {
    setReviewingDraftId(draftId);
    setViewingResultsFor(null);
    loadAll();
  };

  const handlePublished = () => {
    setReviewingDraftId(null);
    loadAll();
  };

  const handleDeleteDocument = (doc) => {
    toast(
      (t) => (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Delete "{doc.title}"?</p>
          <p className="text-xs text-muted">
            Removes all assignments, attempts, and history tied to it. Can't be
            undone.
          </p>
          <div className="flex gap-2 mt-1">
            <button
              onClick={() => {
                toast.dismiss(t.id);
                doDeleteDocument(doc);
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

  const doDeleteDocument = async (doc) => {
    setDeletingDocId(doc.id);
    try {
      await api.delete(`/documents/${doc.id}`);
      toast.success("Document deleted");
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeletingDocId(null);
    }
  };

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-1">
          {profile ? `Welcome back, ${profile.username}` : "Welcome back"}
        </h1>
        <p className="text-muted text-sm">
          Create assignments from your course material and track how your
          students do.
        </p>
      </div>

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mb-6">
          {error}
        </p>
      )}

      <div className="bg-surface border border-border rounded-xl p-5 mb-8">
        <h2 className="font-semibold mb-4">Create an assignment</h2>
        {loading ? (
          <Skeleton className="h-24" />
        ) : (
          <CreateAssignmentForm
            documents={documents}
            onDraftCreated={handleDraftCreated}
          />
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-10">
        <div>
          <h2 className="text-lg font-semibold mb-4">Your assignments</h2>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
          ) : assignments.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-border rounded-xl">
              <p className="text-muted text-sm">
                No assignments yet. Create one above.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {assignments.map((a) => (
                <AssignmentCard
                  key={a.id}
                  assignment={a}
                  selected={
                    viewingResultsFor === a.id || reviewingDraftId === a.id
                  }
                  onViewResults={(id) => {
                    setViewingResultsFor(id);
                    setReviewingDraftId(null);
                  }}
                  onReview={(id) => {
                    setReviewingDraftId(id);
                    setViewingResultsFor(null);
                  }}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-4">
            {reviewingDraftId ? "Review draft" : "Results"}
          </h2>
          {reviewingDraftId ? (
            <ReviewDraftPanel
              draftId={reviewingDraftId}
              onPublished={handlePublished}
              onClose={() => setReviewingDraftId(null)}
            />
          ) : viewingResultsFor ? (
            <ResultsPanel
              assignmentId={viewingResultsFor}
              onClose={() => setViewingResultsFor(null)}
            />
          ) : (
            <div className="text-center py-12 border border-dashed border-border rounded-xl">
              <p className="text-muted text-sm">
                Select an assignment to view results, or review a draft.
              </p>
            </div>
          )}
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-4">Your course material</h2>
      <UploadPanel onUploaded={loadAll} />

      {/* Bulk upload */}
      <div className="bg-surface border border-border rounded-xl p-5 mb-8 mt-6">
        <h2 className="font-semibold mb-1">Bulk upload</h2>
        <p className="text-xs text-muted mb-3">
          Upload multiple PDFs or Word docs at once.
        </p>
        <BulkUploadPanel onUploaded={loadAll} />
      </div>

      {/* Classes */}
      <ClassesSummaryCard />

      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-xl">
          <p className="text-muted text-sm">
            No documents yet. Add one above to start creating assignments.
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="card bg-surface border border-border rounded-xl p-4 flex flex-col gap-2"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium leading-snug">{doc.title}</h3>
                <button
                  onClick={() => handleDeleteDocument(doc)}
                  disabled={deletingDocId === doc.id}
                  className="text-muted hover:text-incorrect transition-colors shrink-0 disabled:opacity-50"
                  aria-label={`Delete ${doc.title}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <p className="text-xs text-muted font-mono">
                {doc.page_count} page{doc.page_count === 1 ? "" : "s"} ·{" "}
                {formatDate(doc.uploaded_at)}
              </p>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default TeacherDashboard;
