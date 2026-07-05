import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { isLoggedIn } from "../api";

/**
 * The actual JWT lives in an HttpOnly cookie now (see Phase F3 - JWT
 * moved off localStorage for XSS protection), so this can't read the
 * token directly. It checks for the presence of the CSRF cookie instead,
 * which flask-jwt-extended sets alongside the JWT with the same expiry -
 * a reliable client-visible proxy for "is there a live session" without
 * ever exposing the token itself to JavaScript.
 *
 * This is a client-side convenience check only, not the real security
 * boundary - every API call is still independently authenticated by the
 * backend via the cookie. A user without a valid session gets past this
 * check trivially (or bypasses it entirely via devtools) but then every
 * subsequent API call still 401s, so nothing is actually exposed.
 */
const PrivateRoute = () => {
  return isLoggedIn() ? <Outlet /> : <Navigate to="/login" />;
};

export default PrivateRoute;
