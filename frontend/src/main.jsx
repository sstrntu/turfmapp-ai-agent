import React from "react";
import { createRoot } from "react-dom/client";
import ChatApp from "./App.jsx";
import "./styles/assistant-thread.css";

const mount = () => {
  const container = document.getElementById("react-chat-root");
  if (!container) {
    return;
  }

  // Avoid double-mounting if Vite's HMR remounts.
  if (container.dataset.reactMounted === "true") {
    return;
  }

  container.dataset.reactMounted = "true";
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <ChatApp />
    </React.StrictMode>,
  );
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount, { once: true });
} else {
  mount();
}
