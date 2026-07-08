import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import usePageTitle from "../hooks/usePageTitle";
import GoogleSignInButton from "../components/GoogleSignInButton";

const PASSWORD_RULES = [
  { label: "8+ characters", test: (p) => p.length >= 8 },
  { label: "Uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "Lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "Number", test: (p) => /\d/.test(p) },
  {
    label: "Special character",
    test: (p) => /[!@#$%^&*()_+\-=[\]{}|;':",./<>?]/.test(p),
  },
];

const SignUp = () => {
  usePageTitle("Sign up");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(
    searchParams.get("role") === "teacher" ? "teacher" : "student",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showStrength, setShowStrength] = useState(false);

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/signup", { username, email, password, role });
      const data = await api.post("/login", { username, password });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem(
        "studymate_session_started_at",
        Date.now().toString(),
      );
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
      const data = await api.post("/auth/google", { credential, role });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem(
        "studymate_session_started_at",
        Date.now().toString(),
      );
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
          <h1 className="text-3xl font-semibold">Create your account</h1>
          <p className="text-muted text-sm mt-2">
            Upload course material, get quizzed, track progress.
          </p>
        </div>

        {/* Role picker shown before Google button so it's set first */}
        <div className="mb-4">
          <label className="block text-sm text-muted mb-1.5">I am a...</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setRole("student")}
              className={`text-sm font-medium rounded-lg py-2.5 border transition-colors ${
                role === "student"
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-muted hover:border-accent/50"
              }`}
            >
              Student
            </button>
            <button
              type="button"
              onClick={() => setRole("teacher")}
              className={`text-sm font-medium rounded-lg py-2.5 border transition-colors ${
                role === "teacher"
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-muted hover:border-accent/50"
              }`}
            >
              Teacher
            </button>
          </div>
        </div>

        <GoogleSignInButton
          onCredential={handleGoogleCredential}
          role={role}
          label="Sign up with Google"
        />

        <div className="flex items-center gap-3 my-4">
          <hr className="flex-1 border-border" />
          <span className="text-xs text-muted">or sign up with email</span>
          <hr className="flex-1 border-border" />
        </div>

        <form onSubmit={handleSignUp} className="space-y-4">
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
            <label className="block text-sm text-muted mb-1">Email</label>
            <input
              type="email"
              className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">Password</label>
            <input
              type="password"
              className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 outline-none focus:border-accent transition-colors"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setShowStrength(true);
              }}
              required
            />
            {showStrength && password.length > 0 && (
              <div className="mt-2 grid grid-cols-2 gap-1">
                {PASSWORD_RULES.map((rule) => {
                  const passed = rule.test(password);
                  return (
                    <p
                      key={rule.label}
                      className={`text-xs flex items-center gap-1 transition-colors ${
                        passed ? "text-correct" : "text-muted"
                      }`}
                    >
                      <span>{passed ? "✓" : "·"}</span>
                      {rule.label}
                    </p>
                  );
                })}
              </div>
            )}
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
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default SignUp;
