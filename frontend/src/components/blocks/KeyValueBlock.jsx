import React from "react";

export const KeyValueBlock = ({ title, pairs = [] }) => {
  if (!pairs.length) {
    return null;
  }

  return (
    <div className="assistant-widget key-value-widget">
      {title && <div className="widget-title">{title}</div>}
      <dl className="key-value-grid">
        {pairs.map(({ label, value }, index) => (
          <React.Fragment key={`kv-${index}`}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </React.Fragment>
        ))}
      </dl>
    </div>
  );
};
