import React from "react";

export const TypingIndicator = ({ text = "Thinking" }) => (
  <div className="assistant-message typing-indicator-bubble">
    <div className="typing-indicator">
      <span className="thinking-text">{text}</span>
    </div>
  </div>
);
