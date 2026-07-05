import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      await api.post("/reset-password", { token, new_password: password });
      setDone(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg px-4">
        <div className="w-full max-w-sm text-center">
          <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2 mb-4">
            This reset link is missing its token. Request a new one.
          </p>
          <Link to="/forgot-password" className="text-accent hover:underline">
            Back to forgot password
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="font-mono text-accent text-xs tracking-[0.3em] uppercase mb-2">
            StudyMate
          </p>
          <h1 className="text-3xl font-semibold">Choose a new password</h1>
        </div>

        {done ? (
          <p className="text-correct text-sm border border-correct/30 bg-correct/10 rounded-lg px-3 py-2 text-center">
            Password updated. Redirecting to sign in...
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-muted mb-1">
                New password
              </label>
              <input
                type="password"
                className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">
                Confirm new password
              </label>
              <input
                type="password"
                className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={6}
              />
            </div>

            {error && (
              <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent text-bg font-semibold rounded-lg py-2.5 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? "Updating..." : "Update password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPassword;
