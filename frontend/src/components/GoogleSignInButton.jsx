import React, { useEffect, useRef } from "react";

/**
 * Renders Google's own sign-in button using the GIS SDK loaded in index.html.
 * On credential response, calls onCredential(idToken, role).
 *
 * GOOGLE_CLIENT_ID must be set in frontend/.env as VITE_GOOGLE_CLIENT_ID.
 * Without it, this renders nothing rather than crashing.
 */
const GoogleSignInButton = ({ onCredential, role = "student", label = "Continue with Google" }) => {
  const divRef = useRef(null);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !window.google || !divRef.current) return;

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => {
        if (response.credential) {
          onCredential(response.credential, role);
        }
      },
    });

    window.google.accounts.id.renderButton(divRef.current, {
      theme: "outline",
      size: "large",
      width: divRef.current.offsetWidth || 360,
      text: label === "Continue with Google" ? "continue_with" : "signin_with",
    });
  }, [clientId, role]);

  if (!clientId) return null;

  return <div ref={divRef} className="w-full" />;
};

export default GoogleSignInButton;
