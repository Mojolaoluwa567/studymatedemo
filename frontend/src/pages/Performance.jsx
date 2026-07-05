import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api, formatDuration, formatDate, difficultyLabel } from "../api";
import Layout from "../components/Layout";
import BackButton from "../components/BackButton";

const DIFFICULTY_COLORS = {
  easy: "#5FB89C",
  hard: "#F2B544",
  difficult: "#E85D4A",
  lecturer_style: "#94A3B8",
};

const Performance = () => {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/documents/${id}/performance`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <Layout>
        <BackButton />
        <p className="text-incorrect">{error}</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <BackButton />
        <p className="text-muted text-sm">Loading...</p>
      </Layout>
    );
  }

  const chartData = data.attempts.map((a, idx) => ({
    name: `#${idx + 1}`,
    percentage: a.percentage,
    difficulty: a.difficulty,
    date: formatDate(a.submitted_at),
  }));

  return (
    <Layout>
      <BackButton />
      <h1 className="text-2xl font-semibold mb-1">{data.document_title}</h1>
      <p className="text-muted text-sm mb-8">
        Total study time logged:{" "}
        <span className="font-mono text-ink">
          {formatDuration(data.total_study_seconds)}
        </span>
      </p>

      {data.attempts.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-border rounded-xl">
          <p className="text-muted mb-4">
            No quizzes taken yet for this document.
          </p>
          <Link
            to={`/documents/${id}/quiz-setup`}
            className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity inline-block"
          >
            Take your first quiz
          </Link>
        </div>
      ) : (
        <>
          <div className="bg-surface border border-border rounded-xl p-5 mb-8">
            <p className="text-sm text-muted mb-4">
              Score over time across attempts
            </p>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#2C2935" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#9C99A8" fontSize={12} />
                  <YAxis
                    stroke="#9C99A8"
                    fontSize={12}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1A1820",
                      border: "1px solid #2C2935",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(value, name, props) => [
                      `${value}%`,
                      props.payload.difficulty,
                    ]}
                    labelFormatter={(label, payload) =>
                      payload?.[0]?.payload?.date || label
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="percentage"
                    stroke="#F2B544"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="space-y-2">
            {data.attempts
              .slice()
              .reverse()
              .map((a, idx) => (
                <div
                  key={a.attempt_id}
                  className="bg-surface border border-border rounded-xl px-4 py-3 flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="font-mono text-xs px-2 py-0.5 rounded border"
                      style={{
                        color: DIFFICULTY_COLORS[a.difficulty],
                        borderColor: DIFFICULTY_COLORS[a.difficulty],
                      }}
                    >
                      {difficultyLabel(a.difficulty)}
                    </span>
                    <span className="text-muted">
                      {formatDate(a.submitted_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-muted text-xs">
                      study time: {formatDuration(a.study_time_seconds)}
                    </span>
                    <span className="font-mono">{a.percentage}%</span>
                  </div>
                </div>
              ))}
          </div>
        </>
      )}

      <div className="mt-8">
        <Link
          to={`/documents/${id}/quiz-setup`}
          className="bg-accent text-bg font-semibold rounded-lg px-5 py-2 hover:opacity-90 transition-opacity inline-block"
        >
          Take another quiz
        </Link>
      </div>
    </Layout>
  );
};

export default Performance;
