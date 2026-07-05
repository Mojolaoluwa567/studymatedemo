import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { isLoggedIn } from "../api";

const WARNING_MINUTES_BEFORE = 5;
// Must match backend's JWT_ACCESS_TOKEN_EXPIRES (app.py). The JWT itself
// lives in an HttpOnly cookie now (Phase F3), so the frontend can no
// longer decode its exp claim directly - this hardcoded window plus a
// per-session login timestamp is the practical substitute.
const SESSION_LENGTH_MINUTES = 24 * 60;
const LOGIN_TIME_KEY = "studymate_session_started_at";

/**
 * Schedules a one-time toast warning shortly before the current session
 * expires, so a session doesn't just go dead mid-task with no warning.
 * Re-login is cheap (no unsaved client-side state to lose - everything
 * is already persisted server-side as it happens), so this is just a
 * heads-up, not a blocking modal or auto-refresh.
 *
 * The login timestamp itself (not the token) is what's stored client-side
 * - it's not a secret, just a clock reference, so storing it in
 * localStorage carries none of the risk that storing the actual JWT did.
 */
export default function useSessionExpiryWarning() {
  const warnedRef = useRef(false);

  useEffect(() => {
    if (!isLoggedIn()) return;

    let startedAt = localStorage.getItem(LOGIN_TIME_KEY);
    if (!startedAt) {
      // First time this hook runs for a live session - record now as the
      // best available approximation of session start.
      startedAt = Date.now().toString();
      localStorage.setItem(LOGIN_TIME_KEY, startedAt);
    }

    const expiresAt = Number(startedAt) + SESSION_LENGTH_MINUTES * 60 * 1000;
    const warnAt = expiresAt - WARNING_MINUTES_BEFORE * 60 * 1000;
    const msUntilWarning = warnAt - Date.now();

    if (msUntilWarning <= 0 || warnedRef.current) return;

    const timer = setTimeout(() => {
      if (warnedRef.current) return;
      warnedRef.current = true;
      toast(
        "Your session will expire soon. Save anything important and log in again if needed.",
        { icon: "⏳", duration: 8000 }
      );
    }, msUntilWarning);

    return () => clearTimeout(timer);
  }, []);
}
