import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { api } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const JoinAssignment = () => {
  usePageTitle("Join a Quiz");
  const navigate = useNavigate();
  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setError("");
    setJoining(true);
    try {
      const quiz = await api.post("/assignments/join", {
        join_code: joinCode.trim(),
      });
      navigate(`/quiz/${quiz.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setJoining(false);
    }
  };

  return (
    <Layout>
      <BackButton />
      <div className="max-w-sm mx-auto py-12 text-center">
        <h1 className="text-2xl font-semibold mb-2">Join an assignment</h1>
        <p className="text-muted text-sm mb-8">
          Enter the join code your teacher shared with you.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            placeholder="e.g. 9AZELC"
            maxLength={10}
            className="w-full text-center font-mono text-2xl tracking-[0.3em] uppercase bg-surface border border-border rounded-lg px-4 py-3 outline-none focus:border-accent transition-colors"
            autoFocus
          />

          {error && (
            <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={joining || !joinCode.trim()}
            className="w-full flex items-center justify-center gap-2 bg-accent text-bg font-semibold rounded-lg py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {!joining && <LogIn size={16} />}
            {joining ? "Joining..." : "Join quiz"}
          </button>
        </form>
      </div>
    </Layout>
  );
};

export default JoinAssignment;
