import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { api } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const LEVEL_STYLES = {
  high: "border-incorrect/30 bg-incorrect/10 text-incorrect",
  medium: "border-accent/30 bg-accent-soft text-accent",
  low: "border-border bg-surface text-muted",
};

const ClassRisk = () => {
  const { id } = useParams();
  usePageTitle("At-Risk Students");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/classes/${id}/risk`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <Layout>
        <BackButton />
        <p className="text-incorrect text-sm">{error}</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <BackButton />
        <p className="text-muted text-sm">
          Checking student activity... this can take a moment.
        </p>
      </Layout>
    );
  }

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1 flex items-center gap-2">
        <AlertTriangle size={20} className="text-accent" /> {data.class_name} —
        At Risk
      </h1>
      <p className="text-muted text-sm mb-6">
        {data.flagged_count} of {data.total_students} student
        {data.total_students !== 1 ? "s" : ""} flagged for review.
      </p>

      {data.students.length === 0 && (
        <p className="text-muted text-sm">
          No students currently show signs of falling behind. 🎉
        </p>
      )}

      <div className="flex flex-col gap-3">
        {data.students.map((s) => (
          <div
            key={s.student_id}
            className={`card border rounded-xl p-4 ${LEVEL_STYLES[s.level]}`}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="font-medium">{s.username}</p>
              <span className="text-xs font-mono uppercase">
                {s.level} risk
              </span>
            </div>
            <ul className="text-sm space-y-1 mb-2">
              {s.reasons.map((r, i) => (
                <li key={i}>• {r}</li>
              ))}
            </ul>
            {s.ai_suggestion && (
              <p className="text-xs text-muted italic mt-2 pt-2 border-t border-border/50">
                Suggestion: {s.ai_suggestion}
              </p>
            )}
          </div>
        ))}
      </div>
    </Layout>
  );
};

export default ClassRisk;
