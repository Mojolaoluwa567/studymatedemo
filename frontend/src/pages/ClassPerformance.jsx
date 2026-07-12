import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp } from "lucide-react";
import { api } from "../api";
import Layout from "../components/Layout";
import usePageTitle from "../hooks/usePageTitle";
import BackButton from "../components/BackButton";

const ClassPerformance = () => {
  const { id } = useParams();
  usePageTitle("Class Performance");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [downloadingGradebook, setDownloadingGradebook] = useState(false);

  const handleDownloadGradebook = async () => {
    setDownloadingGradebook(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:5000"}/classes/${id}/gradebook-export`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) throw new Error("Could not generate the gradebook.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "gradebook.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    } finally {
      setDownloadingGradebook(false);
    }
  };

  useEffect(() => {
    api
      .get(`/classes/${id}/performance`)
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
        <p className="text-muted text-sm">Loading class performance...</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <BackButton />
      <div className="flex items-start justify-between mb-1">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <TrendingUp size={20} className="text-accent" /> {data.class_name}
        </h1>
        <button
          onClick={handleDownloadGradebook}
          disabled={downloadingGradebook}
          className="text-xs border border-border rounded-lg px-3 py-1.5 hover:border-accent transition-colors disabled:opacity-50"
        >
          {downloadingGradebook ? "Preparing..." : "Download gradebook PDF"}
        </button>
      </div>
      <p className="text-muted text-sm mb-6">
        {data.member_count} student{data.member_count !== 1 ? "s" : ""} · Class
        average:{" "}
        <span className="text-accent font-mono">{data.class_average}%</span>
      </p>

      {data.trend.length > 0 && (
        <div className="card bg-surface border border-border rounded-xl p-5 mb-6">
          <p className="text-sm text-muted mb-3">Class average over time</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.trend}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgb(var(--color-border))"
              />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="average_percentage"
                stroke="rgb(var(--color-accent))"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.topic_breakdown.length > 0 && (
        <div className="card bg-surface border border-border rounded-xl p-5 mb-6">
          <p className="text-sm text-muted mb-3">
            Class-wide topic mastery (weakest first)
          </p>
          <ResponsiveContainer
            width="100%"
            height={Math.max(180, data.topic_breakdown.length * 36)}
          >
            <BarChart
              data={data.topic_breakdown}
              layout="vertical"
              margin={{ left: 80 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgb(var(--color-border))"
              />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="topic"
                tick={{ fontSize: 11 }}
                width={100}
              />
              <Tooltip />
              <Bar
                dataKey="mastery_percentage"
                fill="rgb(var(--color-accent))"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.assignments.length > 0 && (
        <div className="card bg-surface border border-border rounded-xl p-5 mb-6">
          <p className="text-sm text-muted mb-3">Assignment completion</p>
          <div className="flex flex-col gap-2">
            {data.assignments.map((a) => (
              <div
                key={a.quiz_id}
                className="flex items-center justify-between text-sm"
              >
                <span>{a.title}</span>
                <span className="text-muted">
                  {a.submitted_count}/{a.member_count} ({a.completion_rate}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card bg-surface border border-border rounded-xl p-5">
        <p className="text-sm text-muted mb-3">
          Students (weakest average first)
        </p>
        <div className="flex flex-col gap-2">
          {data.students.map((s) => (
            <div
              key={s.student_id}
              className="flex items-center justify-between text-sm py-2 border-b border-border last:border-0"
            >
              <span>{s.username}</span>
              <span className="flex items-center gap-3 text-muted">
                {s.attempts_count} attempt{s.attempts_count !== 1 ? "s" : ""}
                <span className="font-mono text-accent">
                  {s.average_percentage}%
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
};

export default ClassPerformance;
