import React, { Suspense, lazy } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import PrivateRoute from "./security/PrivateRoute";

// Landing and auth pages stay eagerly loaded - they're the very first
// thing anyone sees, and are small/light compared to the authenticated
// app. Everything past login is lazy-loaded so a first-time visitor
// isn't downloading the entire app (charts, PDF export, etc.) just to
// see the landing page.
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

const DashboardRouter = lazy(() => import("./pages/DashboardRouter"));
const JoinAssignment = lazy(() => import("./pages/JoinAssignment"));
const StudySession = lazy(() => import("./pages/StudySession"));
const QuizSetup = lazy(() => import("./pages/QuizSetup"));
const Quiz = lazy(() => import("./pages/Quiz"));
const Results = lazy(() => import("./pages/Results"));
const Performance = lazy(() => import("./pages/Performance"));
const PerformanceOverview = lazy(() => import("./pages/PerformanceOverview"));
const Achievements = lazy(() => import("./pages/Achievements"));
const History = lazy(() => import("./pages/History"));
const Profile = lazy(() => import("./pages/Profile"));
const Classes = lazy(() => import("./pages/Classes"));
const ClassPerformance = lazy(() => import("./pages/ClassPerformance"));
const ClassRisk = lazy(() => import("./pages/ClassRisk"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const NotFound = lazy(() => import("./pages/NotFound"));

const RouteFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-bg">
    <div className="w-8 h-8 rounded-lg bg-accent animate-pulse" />
  </div>
);

const App = () => {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "rgb(var(--color-surface))",
            color: "rgb(var(--color-ink))",
            border: "1px solid rgb(var(--color-border))",
          },
        }}
      />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route element={<PrivateRoute />}>
            <Route path="/dashboard" element={<DashboardRouter />} />
            <Route path="/join" element={<JoinAssignment />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/classes" element={<Classes />} />
            <Route
              path="/classes/:id/performance"
              element={<ClassPerformance />}
            />
            <Route path="/classes/:id/risk" element={<ClassRisk />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/documents/:id/study" element={<StudySession />} />
            <Route path="/documents/:id/quiz-setup" element={<QuizSetup />} />
            <Route
              path="/documents/:id/performance"
              element={<Performance />}
            />
            <Route path="/performance" element={<PerformanceOverview />} />
            <Route path="/achievements" element={<Achievements />} />
            <Route path="/history" element={<History />} />
            <Route path="/quiz/:quizId" element={<Quiz />} />
            <Route path="/results/:attemptId" element={<Results />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
};

export default App;
