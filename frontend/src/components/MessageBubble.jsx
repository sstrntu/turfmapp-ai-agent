import React from "react";
import { AssistantMessage } from "./AssistantMessage.jsx";
import { UserMessage } from "./UserMessage.jsx";

export const MessageBubble = ({ message }) => {
  if (!message) return null;

  switch (message.role) {
    case "assistant":
      return <AssistantMessage message={message} />;
    case "user":
      return <UserMessage message={message} />;
    default:
      return null;
  }
};
