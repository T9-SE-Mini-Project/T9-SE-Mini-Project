import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// Apply a saved theme before the first paint so the page doesn't flash the wrong colours.
try {
  const theme = localStorage.getItem("bbms.theme");
  if (theme) document.documentElement.dataset.theme = theme;
} catch {
  // Storage unavailable: follow the system theme.
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
