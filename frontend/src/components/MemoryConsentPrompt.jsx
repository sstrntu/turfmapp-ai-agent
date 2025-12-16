import React from "react";

export const MemoryConsentPrompt = ({ facts = [], conversationId, onDecision }) => {
  if (!Array.isArray(facts) || facts.length === 0) {
    return null;
  }

  const [status, setStatus] = React.useState("pending");
  const token = window?.supabase?.getAccessToken?.();

  const handleApprove = async () => {
    if (!token) {
      setStatus("error");
      return;
    }
    try {
      setStatus("saving");
      const response = await fetch("/api/v1/memory/approve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ facts, conversation_id: conversationId }),
      });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      setStatus("saved");
      onDecision?.("approved");
    } catch (error) {
      console.error("Memory approval failed", error);
      setStatus("error");
    }
  };

  const handleDecline = () => {
    setStatus("dismissed");
    onDecision?.("declined");
  };

  if (status === "dismissed") {
    return null;
  }

  return (
    <div className="memory-consent" style={{ margin: "0.75rem 0" }}>
      <div className="memory-title" style={{ marginBottom: "0.5rem", fontWeight: 600 }}>
        Before I remember anything long-term, do you want me to remember:
      </div>
      <ul className="memory-facts" style={{ margin: "0 0 0.75rem 1rem", padding: 0 }}>
        {facts.map((fact) => (
          <li key={fact.key}>
            <strong>{fact.key.replace(/_/g, " ")}</strong>: {fact.value}
          </li>
        ))}
      </ul>
      <div className="memory-actions" style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" onClick={handleApprove} disabled={status === "saving" || status === "saved"}>
          {status === "saving" ? "Saving..." : status === "saved" ? "Saved" : "Yes, remember this"}
        </button>
        {status !== "saved" && (
          <button type="button" onClick={handleDecline} disabled={status === "saving"}>
            No, thanks
          </button>
        )}
      </div>
      {status === "error" && (
        <div className="memory-status error">Couldn't save memory. Please try again later.</div>
      )}
    </div>
  );
};
