import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Remove the static first-paint loading screen now that React has taken
// over rendering - a tiny timeout avoids a jarring instant swap if the
// app's own first paint isn't quite ready yet.
const initialLoader = document.getElementById("initial-loader");
if (initialLoader) {
  setTimeout(() => initialLoader.remove(), 80);
}
