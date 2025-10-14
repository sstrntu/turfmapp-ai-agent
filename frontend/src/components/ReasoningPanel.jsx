import React from "react";

export const ReasoningPanel = ({ reasoning = [] }) => {
  const [open, setOpen] = React.useState(false);
  const entries = Array.isArray(reasoning) ? reasoning : [reasoning];
  const filtered = entries.filter(Boolean);

  if (filtered.length === 0) {
    return null;
  }

  return (
    <div className="assistant-group reasoning-group">
      <button
        type="button"
        className="reason-chip"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        {open ? "Hide reasoning" : "Show reasoning"}
      </button>
      {open && (
        <div className="reason-panel">
          {filtered.map((entry, index) => (
            <p key={`reason-${index}`}>{entry}</p>
          ))}
        </div>
      )}
    </div>
  );
};
