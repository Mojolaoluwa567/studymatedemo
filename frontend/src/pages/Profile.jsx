import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  User,
  Mail,
  Calendar,
  Flame,
  Zap,
  Lock,
  Target,
  FileText,
  Trophy,
  KeyRound,
} from "lucide-react";
import { api, formatDate } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import StatCard from "../components/StatCard";
import BackButton from "../components/BackButton";

const AchievementBadge = ({ achievement }) => (
  <div
    className={`rounded-xl border p-4 text-center transition-colors ${
      achievement.unlocked
        ? "border-accent/30 bg-accent-soft"
        : "border-border bg-surface opacity-50"
    }`}
  >
    {achievement.unlocked ? (
      <Trophy size={24} className="text-accent mx-auto mb-1" />
    ) : (
      <Lock size={24} className="text-muted mx-auto mb-1" />
    )}
    <p className="text-sm font-medium">{achievement.title}</p>
    <p className="text-xs text-muted mt-1">{achievement.description}</p>
  </div>
);

const Profile = () => {
  usePageTitle("Profile");
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [achievements, setAchievements] = useState(null);
  const [error, setError] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changing, setChanging] = useState(false);
  const [pwError, setPwError] = useState("");

  useEffect(() => {
    api
      .get("/profile")
      .then(setProfile)
      .catch((err) => setError(err.message));
    api
      .get("/profile/stats")
      .then(setStats)
      .catch(() => {});
    api
      .get("/achievements")
      .then((data) => setAchievements(data.achievements))
      .catch(() => {});
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError("");

    if (newPassword !== confirmPassword) {
      setPwError("New passwords do not match");
      return;
    }

    setChanging(true);
    try {
      await api.post("/profile/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success("Password updated");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwError(err.message);
    } finally {
      setChanging(false);
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

  if (!profile) {
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
      <h1 className="text-2xl font-semibold mb-1">Profile</h1>
      <p className="text-muted text-sm mb-8">
        Account details and your study stats.
      </p>

      <div className="bg-surface border border-border rounded-xl p-5 mb-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-14 h-14 rounded-full bg-accent-soft border border-accent/30 flex items-center justify-center font-mono text-xl text-accent">
            {profile.username[0]?.toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-lg flex items-center gap-2">
              <User size={15} className="text-muted" /> {profile.username}
            </p>
            <p className="text-muted text-sm flex items-center gap-1.5">
              <Mail size={13} className="text-muted" /> {profile.email}
            </p>
          </div>
        </div>
        {profile.member_since && (
          <p className="text-xs text-muted font-mono flex items-center gap-1.5">
            <Calendar size={11} /> Member since{" "}
            {formatDate(profile.member_since)}
          </p>
        )}
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard
            label="Quizzes taken"
            value={stats.total_quizzes}
            icon={<Zap size={16} />}
          />
          <StatCard
            label="Documents uploaded"
            value={stats.total_documents}
            icon={<FileText size={16} />}
          />
          <StatCard
            label="Avg. score"
            value={`${stats.average_score}%`}
            icon={<Target size={16} />}
          />
          <StatCard
            label="Day streak"
            value={stats.current_streak}
            icon={<Flame size={16} />}
          />
        </div>
      )}

      {achievements && (
        <div className="mb-8">
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <Trophy size={16} className="text-accent" /> Achievements
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {achievements.map((a) => (
              <AchievementBadge key={a.key} achievement={a} />
            ))}
          </div>
        </div>
      )}

      <div className="bg-surface border border-border rounded-xl p-5 max-w-md">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <KeyRound size={16} className="text-muted" /> Change password
        </h2>
        <form onSubmit={handleChangePassword} className="space-y-3">
          <div>
            <label className="block text-sm text-muted mb-1">
              Current password
            </label>
            <input
              type="password"
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">
              New password
            </label>
            <input
              type="password"
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
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
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 outline-none focus:border-accent transition-colors"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          {pwError && (
            <p className="text-incorrect text-sm border border-incorrect/30 bg-incorrect/10 rounded-lg px-3 py-2">
              {pwError}
            </p>
          )}

          <button
            type="submit"
            disabled={changing}
            className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {changing ? "Updating..." : "Update password"}
          </button>
        </form>
      </div>
    </Layout>
  );
};

export default Profile;
