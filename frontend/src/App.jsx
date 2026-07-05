import React from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import DashboardRouter from "./pages/DashboardRouter";
import JoinAssignment from "./pages/JoinAssignment";
import StudySession from "./pages/StudySession";
import QuizSetup from "./pages/QuizSetup";
import Quiz from "./pages/Quiz";
import Results from "./pages/Results";
import Performance from "./pages/Performance";
import History from "./pages/History";
import Profile from "./pages/Profile";
import Classes from "./pages/Classes";
import AdminDashboard from "./pages/AdminDashboard";
import NotFound from "./pages/NotFound";
import PrivateRoute from "./security/PrivateRoute";

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
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/documents/:id/study" element={<StudySession />} />
          <Route path="/documents/:id/quiz-setup" element={<QuizSetup />} />
          <Route path="/documents/:id/performance" element={<Performance />} />
          <Route path="/history" element={<History />} />
          <Route path="/quiz/:quizId" element={<Quiz />} />
          <Route path="/results/:attemptId" element={<Results />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
