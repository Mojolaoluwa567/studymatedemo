import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Users2,
  Copy,
  Trash2,
  LogIn as JoinIcon,
  BookOpen,
} from "lucide-react";
import { api, formatDate } from "../api";
import Layout from "../components/Layout";
import BackButton from "../components/BackButton";
import Skeleton from "../components/Skeleton";
import usePageTitle from "../hooks/usePageTitle";

const ClassAnnouncements = ({ classId, isTeacher }) => {
  const [announcements, setAnnouncements] = useState(null);
  const [message, setMessage] = useState("");
  const [posting, setPosting] = useState(false);

  const load = () => {
    api
      .get(`/classes/${classId}/announcements`)
      .then((data) => setAnnouncements(data.announcements))
      .catch(() => {});
  };

  useEffect(() => {
    load();
  }, [classId]);

  const handlePost = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setPosting(true);
    try {
      await api.post(`/classes/${classId}/announcements`, { message });
      setMessage("");
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/announcements/${id}`);
      load();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="mb-4 pb-4 border-b border-border">
      <p className="text-xs text-muted mb-2">Announcements</p>

      {isTeacher && (
        <form onSubmit={handlePost} className="flex gap-2 mb-3">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Post an announcement to this class..."
            className="flex-1 bg-bg border border-border rounded-lg px-3 py-1.5 text-xs outline-none focus:border-accent transition-colors"
          />
          <button
            type="submit"
            disabled={posting}
            className="bg-accent text-bg text-xs font-medium rounded-lg px-3 py-1.5 hover:opacity-90 disabled:opacity-50"
          >
            {posting ? "Posting..." : "Post"}
          </button>
        </form>
      )}

      {announcements === null ? (
        <Skeleton className="h-10" />
      ) : announcements.length === 0 ? (
        <p className="text-xs text-muted">No announcements yet.</p>
      ) : (
        <div className="space-y-2">
          {announcements.map((a) => (
            <div
              key={a.id}
              className="flex items-start justify-between gap-2 text-xs bg-bg border border-border rounded-lg px-3 py-2"
            >
              <div>
                <p>{a.message}</p>
                <p className="text-muted mt-1">{formatDate(a.created_at)}</p>
              </div>
              {isTeacher && (
                <button
                  onClick={() => handleDelete(a.id)}
                  className="text-incorrect shrink-0"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const Classes = () => {
  usePageTitle("Classes");
  const [role, setRole] = useState(
    () => localStorage.getItem("studymate_role") || null,
  );
  const [classes, setClasses] = useState(null);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedDetail, setExpandedDetail] = useState(null);

  const load = () => {
    api
      .get("/profile")
      .then((p) => {
        setRole(p.role);
        localStorage.setItem("studymate_role", p.role);
      })
      .catch(() => {});
    api
      .get("/classes")
      .then((d) => setClasses(d.classes))
      .catch((err) => setError(err.message));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.post("/classes", { name: newName.trim() });
      toast.success("Class created");
      setNewName("");
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true);
    try {
      await api.post("/classes/join", {
        join_code: joinCode.trim().toUpperCase(),
      });
      toast.success("Joined class");
      setJoinCode("");
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setJoining(false);
    }
  };

  const handleDelete = async (id, name) => {
    try {
      await api.delete(`/classes/${id}`);
      toast.success(`"${name}" deleted`);
      load();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    setExpandedDetail(null);
    try {
      const detail = await api.get(`/classes/${id}`);
      setExpandedDetail(detail);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleCopyCode = (code) => {
    navigator.clipboard?.writeText(code);
    toast.success("Class code copied");
  };

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1 flex items-center gap-2">
        <Users2 size={22} className="text-accent" /> Classes
      </h1>
      <p className="text-muted text-sm mb-8">
        {role === "teacher"
          ? "Create a class, share the code once, and every assignment you tag to it becomes visible to all members automatically."
          : "Join a class with a code from your teacher to see every assignment they've shared, all in one place."}
      </p>

      {error && (
        <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mb-6">
          {error}
        </p>
      )}

      {role === "teacher" ? (
        <div className="bg-surface border border-border rounded-xl p-5 mb-8">
          <h2 className="font-semibold mb-1">Create a class</h2>
          <p className="text-xs text-muted mb-3">
            Give it a name your students will recognize, like "CS 301 - Morning
            Section."
          </p>
          <form
            onSubmit={handleCreate}
            className="flex flex-col sm:flex-row gap-2"
          >
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Class name"
              className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
            />
            <button
              type="submit"
              disabled={creating}
              className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 text-sm hover:opacity-90 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create class"}
            </button>
          </form>
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-xl p-5 mb-8">
          <h2 className="font-semibold mb-1 flex items-center gap-2">
            <JoinIcon size={16} /> Join a class
          </h2>
          <p className="text-xs text-muted mb-3">
            Enter the code your teacher shared with you.
          </p>
          <form
            onSubmit={handleJoin}
            className="flex flex-col sm:flex-row gap-2"
          >
            <input
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              placeholder="e.g. AB12CD"
              className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent transition-colors font-mono uppercase"
            />
            <button
              type="submit"
              disabled={joining}
              className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 text-sm hover:opacity-90 disabled:opacity-50"
            >
              {joining ? "Joining..." : "Join"}
            </button>
          </form>
        </div>
      )}

      <h2 className="text-lg font-semibold mb-4">
        {role === "teacher" ? "Your classes" : "Classes you've joined"}
      </h2>

      {classes === null ? (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : classes.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-xl">
          <Users2 size={28} className="text-muted mx-auto mb-3" />
          <p className="text-muted text-sm">
            {role === "teacher"
              ? "No classes yet. Create one above."
              : "You haven't joined any classes yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {classes.map((c) => (
            <div
              key={c.id}
              className="bg-surface border border-border rounded-xl p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted font-mono mt-0.5">
                    {c.member_count} member{c.member_count === 1 ? "" : "s"} ·
                    created {formatDate(c.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {role === "teacher" && (
                    <button
                      onClick={() => handleCopyCode(c.join_code)}
                      className="flex items-center gap-1 text-xs font-mono border border-border rounded-lg px-2.5 py-1.5 hover:border-accent transition-colors"
                    >
                      <Copy size={11} /> {c.join_code}
                    </button>
                  )}
                  {role === "teacher" && (
                    <Link
                      to={`/classes/${c.id}/performance`}
                      className="text-xs text-accent hover:underline"
                    >
                      Performance
                    </Link>
                  )}
                  {role === "teacher" && (
                    <Link
                      to={`/classes/${c.id}/risk`}
                      className="text-xs text-accent hover:underline"
                    >
                      At Risk
                    </Link>
                  )}
                  <button
                    onClick={() => handleExpand(c.id)}
                    className="text-xs text-accent hover:underline"
                  >
                    {expandedId === c.id ? "Hide" : "View assignments"}
                  </button>
                  {role === "teacher" && (
                    <button
                      onClick={() => handleDelete(c.id, c.name)}
                      className="text-incorrect hover:text-incorrect/80"
                      title="Delete class"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>

              {expandedId === c.id && (
                <div className="mt-4 pt-4 border-t border-border">
                  <ClassAnnouncements
                    classId={c.id}
                    isTeacher={role === "teacher"}
                  />
                  {!expandedDetail ? (
                    <Skeleton className="h-16" />
                  ) : expandedDetail.assignments.length === 0 ? (
                    <p className="text-xs text-muted">
                      No assignments tagged to this class yet.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {expandedDetail.assignments.map((a) => (
                        <div
                          key={a.id}
                          className="flex items-center justify-between text-sm border border-border rounded-lg px-3 py-2"
                        >
                          <div className="flex items-center gap-2">
                            <BookOpen size={13} className="text-muted" />
                            <span>{a.title}</span>
                          </div>
                          {role !== "teacher" && (
                            <Link
                              to={`/join`}
                              className="text-xs text-accent hover:underline"
                            >
                              Join with code {a.join_code}
                            </Link>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default Classes;
