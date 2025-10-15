import React from "react";

export const SearchResultsBlock = ({ results = [], title = "Search results" }) => {
  if (!Array.isArray(results) || results.length === 0) {
    return null;
  }

  return (
    <div className="assistant-widget search-widget">
      <div className="widget-title">{title}</div>
      <ul className="search-results-list">
        {results.map((result, index) => {
          const url = result.url || result.link;
          const displayTitle = result.title || url || `Result ${index + 1}`;
          const snippet = result.snippet || result.description || "";
          const favicon = result.favicon || result.icon;
          const source = result.source || result.domain || (url ? new URL(url).hostname : "");

          return (
            <li key={`sr-${index}`} className="search-result-item">
              <div className="search-result-header">
                {favicon && (
                  <img
                    src={favicon}
                    alt=""
                    aria-hidden="true"
                    className="search-favicon"
                    width="16"
                    height="16"
                  />
                )}
                <span className="search-source">{source}</span>
              </div>
              {url ? (
                <a href={url} target="_blank" rel="noopener noreferrer" className="search-title">
                  {displayTitle}
                </a>
              ) : (
                <span className="search-title">{displayTitle}</span>
              )}
              {snippet && <p className="search-snippet">{snippet}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
