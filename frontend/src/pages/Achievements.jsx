import React, { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { api } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const AchievementBadge = ({ achievement }) => (
  <div
    className={`card rounded-xl border p-4 text-center transition-colors ${
      achievement.unlocked
        ? "border-accent/30 bg-accent-soft"
        : "border-border bg-surface opacity-50"
    }`}
  >
    <p className="text-2xl mb-1">{achievement.unlocked ? "🏆" : "🔒"}</p>
    <p className="text-sm font-medium">{achievement.title}</p>
    <p className="text-xs text-muted mt-1">{achievement.description}</p>
  </div>
);

const Achievements = () => {
  usePageTitle("Achievements");
  const [achievements, setAchievements] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/achievements")
      .then((data) => setAchievements(data.achievements))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1 flex items-center gap-2">
        <Trophy size={20} className="text-accent" /> Achievements
      </h1>
      <p className="text-muted text-sm mb-6">
        Milestones you've unlocked (and a few still waiting to be).
      </p>

      {error && <p className="text-incorrect text-sm">{error}</p>}

      {achievements && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {achievements.map((a) => (
            <AchievementBadge key={a.key} achievement={a} />
          ))}
        </div>
      )}
    </Layout>
  );
};

export default Achievements;
