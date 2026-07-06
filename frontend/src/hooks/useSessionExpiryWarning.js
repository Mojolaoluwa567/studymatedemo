import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { getTokenExpiry } from "../api";

const WARNING_MINUTES_BEFORE = 5;

export default function useSessionExpiryWarning() {
  const warnedRef = useRef(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const expiry = getTokenExpiry(token);
    if (!expiry) return;

    const warnAt = expiry.getTime() - WARNING_MINUTES_BEFORE * 60 * 1000;
    const msUntilWarning = warnAt - Date.now();

    if (msUntilWarning <= 0 || warnedRef.current) return;

    const timer = setTimeout(() => {
      if (warnedRef.current) return;
      warnedRef.current = true;
      toast(
        "Your session will expire soon. Save anything important and log in again if needed.",
        { icon: "⏳", duration: 8000 },
      );
    }, msUntilWarning);

    return () => clearTimeout(timer);
  }, []);
}
