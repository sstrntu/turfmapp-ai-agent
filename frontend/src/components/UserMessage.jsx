import React from "react";

const renderParagraphs = (text) => {
  if (!text) return null;
  return text.split(/\n+/).map((line, index) => (
    <p key={`usr-line-${index}`} className="user-line">
      {line}
    </p>
  ));
};

export const UserMessage = ({ message }) => {
  const textContent = React.useMemo(() => {
    if (!Array.isArray(message.content)) {
      return typeof message.content === "string" ? message.content : "";
    }

    return message.content
      .filter((part) => part?.type === "text")
      .map((part) => part.text || "")
      .join("\n\n");
  }, [message.content]);

  return (
    <div className="chat-bubble user message-appear">
      <div className="user-content">{renderParagraphs(textContent)}</div>
    </div>
  );
};
