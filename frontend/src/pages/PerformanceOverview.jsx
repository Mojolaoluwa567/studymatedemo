import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { TrendingUp } from "lucide-react";
import { api, formatDuration } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const PerformanceOverview = () => {
  usePageTitle("Performance");
  const [documents, setDocuments] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/performance/overview")
      .then((data) => setDocuments(data.documents))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1 flex items-center gap-2">
        <TrendingUp size={20} className="text-accent" /> Performance
      </h1>
      <p className="text-muted text-sm mb-6">
        How you're doing across every document you've quizzed on.
      </p>

      {error && <p className="text-incorrect text-sm">{error}</p>}

      {documents && documents.length === 0 && (
        <p className="text-muted text-sm">
          No quiz attempts yet — take a quiz on any document to see your
          performance here.
        </p>
      )}

      {documents && documents.length > 0 && (
        <div className="flex flex-col gap-3">
          {documents.map((d) => (
            <Link
              key={d.document_id}
              to={`/documents/${d.document_id}/performance`}
              className="card bg-surface border border-border rounded-xl p-4 flex items-center justify-between hover:-translate-y-0.5 transition-transform"
            >
              <div>
                <p className="font-medium">{d.document_title}</p>
                <p className="text-xs text-muted mt-1">
                  {d.attempts_count} attempt{d.attempts_count !== 1 ? "s" : ""}{" "}
                  · {formatDuration(d.total_study_seconds)} studied
                </p>
              </div>
              <p className="font-mono text-lg text-accent">
                {d.average_percentage}%
              </p>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default PerformanceOverview;
