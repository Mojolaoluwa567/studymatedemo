import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogIn,
  Clock,
  User,
  Shield,
  LogOut,
  Menu,
  X,
  Users2,
  Trophy,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import { api } from "../api";
import toast from "react-hot-toast";
import ThemeToggle from "./ThemeToggle";
import useSessionExpiryWarning from "../hooks/useSessionExpiryWarning";

const NAV_ICONS = {
  dashboard: <LayoutDashboard size={18} />,
  join: <LogIn size={18} />,
  history: <Clock size={18} />,
  profile: <User size={18} />,
  admin: <Shield size={18} />,
  classes: <Users2 size={18} />,
  achievements: <Trophy size={18} />,
  performance: <TrendingUp size={18} />,
};

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [role, setRole] = useState(
    () => localStorage.getItem("studymate_role") || null,
  );
  const [isAdmin, setIsAdmin] = useState(
    () => localStorage.getItem("studymate_is_admin") === "true",
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  useSessionExpiryWarning();

  useEffect(() => {
    api
      .get("/profile")
      .then((data) => {
        setRole(data.role);
        setIsAdmin(Boolean(data.is_admin));
        localStorage.setItem("studymate_role", data.role);
        localStorage.setItem(
          "studymate_is_admin",
          String(Boolean(data.is_admin)),
        );
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const doLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("studymate_session_started_at");
    localStorage.removeItem("studymate_role");
    localStorage.removeItem("studymate_is_admin");
    navigate("/login");
  };

  const handleLogout = () => {
    toast(
      (t) => (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Log out?</p>
          <p className="text-xs text-muted">
            You'll need to sign in again to continue.
          </p>
          <div className="flex gap-2 mt-1">
            <button
              onClick={() => {
                toast.dismiss(t.id);
                doLogout();
              }}
              className="text-xs bg-incorrect text-bg rounded px-3 py-1.5 font-medium"
            >
              Log out
            </button>
            <button
              onClick={() => toast.dismiss(t.id)}
              className="text-xs border border-border rounded px-3 py-1.5"
            >
              Cancel
            </button>
          </div>
        </div>
      ),
      { duration: 8000 },
    );
  };

  const navItems = [
    { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
    ...(role !== "teacher"
      ? [
          { to: "/join", label: "Join a quiz", icon: "join" },
          { to: "/history", label: "History", icon: "history" },
          { to: "/performance", label: "Performance", icon: "performance" },
          { to: "/achievements", label: "Achievements", icon: "achievements" },
        ]
      : []),
    { to: "/classes", label: "Classes", icon: "classes" },
    { to: "/profile", label: "Profile", icon: "profile" },
    ...(isAdmin ? [{ to: "/admin", label: "Admin", icon: "admin" }] : []),
  ];

  const isActive = (to) =>
    location.pathname === to || location.pathname.startsWith(`${to}/`);

  const UploadShortcut = () =>
    role !== "teacher" && (
      <Link
        to="/dashboard#upload"
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm bg-accent text-bg font-medium hover:opacity-90 transition-opacity mb-2"
      >
        <UploadCloud size={16} />
        Upload document
      </Link>
    );

  const SidebarContent = () => (
    <>
      <Link to="/dashboard" className="flex items-center gap-2 px-2 mb-8">
        <img src="/logoss.png" alt="" className="w-6 h-6" />
        <span className="font-mono text-accent text-xs tracking-[0.3em] uppercase">
          StudyMate
        </span>
      </Link>
      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              isActive(item.to)
                ? "bg-accent-soft text-accent font-medium"
                : "text-muted hover:text-ink hover:bg-surface-light"
            }`}
          >
            {NAV_ICONS[item.icon]}
            {item.label}
          </Link>
        ))}
      </nav>
      <UploadShortcut />
      <div className="pt-4 mt-4 border-t border-border flex items-center justify-between px-2">
        <ThemeToggle />
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-sm text-muted hover:text-incorrect transition-colors"
        >
          <LogOut size={15} /> Log out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-bg text-ink flex">
      <aside className="hidden md:flex flex-col w-60 shrink-0 bg-surface border-r border-border px-3 py-6 sticky top-0 h-screen">
        <SidebarContent />
      </aside>

      <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-bg/95 backdrop-blur border-b border-border flex items-center justify-between px-4 py-3">
        <Link
          to="/dashboard"
          className="flex items-center gap-2 font-mono text-accent text-xs tracking-[0.3em] uppercase"
        >
          <img src="/logoss.png" alt="" className="w-5 h-5" />
          StudyMate
        </Link>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
          className="text-muted hover:text-ink"
        >
          <Menu size={24} />
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-surface border-r border-border px-3 py-6 flex flex-col">
            <div className="flex items-center justify-between px-2 mb-8">
              <span className="flex items-center gap-2 font-mono text-accent text-xs tracking-[0.3em] uppercase">
                <img src="/logoss.png" alt="" className="w-6 h-6" />
                StudyMate
              </span>
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
                className="text-muted hover:text-ink"
              >
                <X size={20} />
              </button>
            </div>
            <nav className="flex-1 flex flex-col gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive(item.to)
                      ? "bg-accent-soft text-accent font-medium"
                      : "text-muted hover:text-ink hover:bg-surface-light"
                  }`}
                >
                  {NAV_ICONS[item.icon]}
                  {item.label}
                </Link>
              ))}
            </nav>
            <UploadShortcut />
            <div className="pt-4 mt-4 border-t border-border flex items-center justify-between px-2">
              <ThemeToggle />
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-sm text-muted hover:text-incorrect"
              >
                <LogOut size={15} /> Log out
              </button>
            </div>
          </aside>
        </div>
      )}

      <main className="flex-1 min-w-0 px-4 sm:px-6 lg:px-10 py-6 sm:py-8 pt-20 md:pt-8 max-w-7xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
};

export default Layout;
