import React from "react";
import { Trophy, Lock } from "lucide-react";

const AchievementBadge = ({ achievement }) => (
  <div
    className={`card rounded-xl border p-4 text-center transition-colors ${
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

export default AchievementBadge;
