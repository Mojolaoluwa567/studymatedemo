import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post("/forgot-password", { email });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="font-mono text-accent text-xs tracking-[0.3em] uppercase mb-2">
            StudyMate
          </p>
          <h1 className="text-3xl font-semibold">Reset your password</h1>
          <p className="text-muted text-sm mt-2">
            Enter the email on your account and we'll send you a reset link.
          </p>
        </div>

        {result ? (
          <div className="space-y-4">
            <p className="text-correct text-sm border border-correct/30 bg-correct/10 rounded-lg px-3 py-2">
              {result.message}
            </p>
            {result.dev_mode && (
              <div className="text-xs border border-border bg-surface rounded-lg px-3 py-2 space-y-2">
                <p className="text-muted">
                  No email server is configured yet, so here's your reset
                  link directly (dev mode):
                </p>
                <Link
                  to={result.reset_link.replace(window.location.origin, "")}
                  className="text-accent break-all hover:underline"
                >
                  {result.reset_link}
                </Link>
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-muted mb-1">Email</label>
              <input
                type="email"
                className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
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
              {loading ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-muted mt-6">
          <Link to="/login" className="text-accent hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;
