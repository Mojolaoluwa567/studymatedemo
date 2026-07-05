import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

/**
 * A consistent "go back" affordance shown at the top of every non-dashboard
 * page. Uses browser history (navigate(-1)) so it goes back to wherever the
 * user actually came from, with a fallback destination for cases where
 * there's no history to go back to (e.g. a page opened directly via URL).
 */
const BackButton = ({ fallback = "/dashboard", label = "Back" }) => {
  const navigate = useNavigate();

  const handleBack = () => {
    if (window.history.length > 2) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  };

  return (
    <button
      onClick={handleBack}
      className="flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors mb-4"
    >
      <ArrowLeft size={15} />
      {label}
    </button>
  );
};

export default BackButton;
