import React from "react";

export const TableBlock = ({ title, headers = [], rows = [] }) => {
  if (!headers.length && !rows.length) {
    return null;
  }

  return (
    <div className="assistant-widget table-widget">
      {title && <div className="widget-title">{title}</div>}
      <div className="widget-table-wrapper">
        <table>
          {headers.length > 0 && (
            <thead>
              <tr>
                {headers.map((header, index) => (
                  <th key={`hdr-${index}`}>{header}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {rows.map((row, rIndex) => (
              <tr key={`row-${rIndex}`}>
                {row.map((cell, cIndex) => (
                  <td key={`cell-${rIndex}-${cIndex}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
