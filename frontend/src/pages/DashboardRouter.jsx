import React, { useEffect, useState } from "react";
import { api } from "../api";
import Layout from "../components/Layout";
import Dashboard from "./Dashboard";
import TeacherDashboard from "./TeacherDashboard";

const DashboardRouter = () => {
  const [role, setRole] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/profile")
      .then((data) => setRole(data.role))
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <Layout>
        <p className="text-incorrect text-sm">{error}</p>
      </Layout>
    );
  }

  if (!role) {
    return (
      <Layout>
        <p className="text-muted text-sm">Loading...</p>
      </Layout>
    );
  }

  return role === "teacher" ? <TeacherDashboard /> : <Dashboard />;
};

export default DashboardRouter;
