import React from "react";
import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import usePageTitle from "../hooks/usePageTitle";

const NotFound = () => {
  usePageTitle("Page not found");

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="text-center max-w-sm">
        <Compass size={40} className="text-muted mx-auto mb-4" />
        <p className="font-mono text-accent text-xs tracking-[0.3em] uppercase mb-2">
          404
        </p>
        <h1 className="text-2xl font-semibold mb-2">Page not found</h1>
        <p className="text-muted text-sm mb-8">
          The page you're looking for doesn't exist or may have moved.
        </p>
        <Link
          to="/dashboard"
          className="inline-block bg-accent text-bg font-semibold rounded-lg px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
