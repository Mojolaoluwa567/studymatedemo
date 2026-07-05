import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import usePageTitle from "../hooks/usePageTitle";
import GoogleSignInButton from "../components/GoogleSignInButton";

const Login = () => {
  usePageTitle("Log in");
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post("/login", { username, password });
      localStorage.setItem("studymate_session_started_at", Date.now().toString());
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCredential = async (credential) => {
    setError("");
    setLoading(true);
    try {
      const data = await api.post("/auth/google", { credential });
      localStorage.setItem("studymate_session_started_at", Date.now().toString());
      navigate("/dashboard");
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
          <h1 className="text-3xl font-semibold">Welcome back</h1>
          <p className="text-muted text-sm mt-2">
            Sign in to keep studying smarter.
          </p>
        </div>

        <GoogleSignInButton
          onCredential={handleGoogleCredential}
          label="Sign in with Google"
        />

        <div className="flex items-center gap-3 my-4">
          <hr className="flex-1 border-border" />
          <span className="text-xs text-muted">or</span>
          <hr className="flex-1 border-border" />
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">Username</label>
            <input
              className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">Password</label>
            <input
              type="password"
              className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm mt-4">
          <Link to="/forgot-password" className="text-muted hover:text-accent transition-colors">
            Forgot password?
          </Link>
        </p>

        <p className="text-center text-sm text-muted mt-6">
          New here?{" "}
          <Link to="/signup" className="text-accent hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
