import React from "react";

export const SourcesPanel = ({ sources = [] }) => {
  const toggleRef = React.useRef(null);
  const popoverRef = React.useRef(null);

  if (!Array.isArray(sources) || sources.length === 0) {
    return null;
  }

  const positionPopover = () => {
    const toggle = toggleRef.current;
    const pop = popoverRef.current;
    if (!toggle || !pop) return;

    // Use fixed positioning to escape scroll container clipping
    pop.style.position = 'fixed';
    // Temporarily show to measure
    pop.style.visibility = 'hidden';
    pop.style.display = 'block';

    const rect = toggle.getBoundingClientRect();
    const spacing = 8;
    let left = rect.left;
    let top = rect.top - pop.offsetHeight - spacing; // place above by default

    // If off top, place below
    if (top < 8) top = rect.bottom + spacing;

    // Constrain horizontally
    const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    const maxLeft = vw - pop.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    if (left < 8) left = 8;

    pop.style.left = `${left}px`;
    pop.style.top = `${top}px`;
    pop.style.visibility = 'visible';
  };

  const closeOnOutside = (event) => {
    const pop = popoverRef.current;
    const toggle = toggleRef.current;
    if (pop && toggle && !pop.contains(event.target) && !toggle.contains(event.target)) {
      pop.style.display = 'none';
      toggle.setAttribute('aria-expanded', 'false');
      window.removeEventListener('scroll', positionPopover, true);
      window.removeEventListener('resize', positionPopover, true);
      document.removeEventListener('mousedown', closeOnOutside, true);
    }
  };

  const toggleOpen = () => {
    const pop = popoverRef.current;
    const toggle = toggleRef.current;
    if (!pop || !toggle) return;

    const isOpen = window.getComputedStyle(pop).display !== 'none';
    if (isOpen) {
      pop.style.display = 'none';
      toggle.setAttribute('aria-expanded', 'false');
      window.removeEventListener('scroll', positionPopover, true);
      window.removeEventListener('resize', positionPopover, true);
      document.removeEventListener('mousedown', closeOnOutside, true);
    } else {
      // Ensure popover is attached to body to avoid clipping/stacking contexts
      if (!pop.parentElement || pop.parentElement.tagName !== 'BODY') {
        document.body.appendChild(pop);
      }
      positionPopover();
      toggle.setAttribute('aria-expanded', 'true');
      window.addEventListener('scroll', positionPopover, true);
      window.addEventListener('resize', positionPopover, true);
      document.addEventListener('mousedown', closeOnOutside, true);
    }
  };

  return (
    <div className="sources-toggle-wrap">
      <button
        ref={toggleRef}
        type="button"
        className="sources-toggle"
        onClick={toggleOpen}
        aria-expanded="false"
      >
        <span className="favicon-stack">
          {sources.slice(0, 3).map((source, index) => {
            const url = source.url || source.link;
            if (!url) return null;

            let faviconUrl;
            try {
              const domain = new URL(url).hostname;
              faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
            } catch {
              return null;
            }

            return (
              <img
                key={index}
                src={faviconUrl}
                alt=""
                width={16}
                height={16}
                loading="lazy"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            );
          })}
        </span>
        <span>Sources</span>
      </button>

      <div
        ref={popoverRef}
        className="sources-popover"
        role="dialog"
        aria-label="Citations"
        style={{ display: 'none' }}
      >
          <ul className="sources-list">
            {sources.slice(0, 10).map((source, index) => {
              const url = source.url || source.link;
              const title = source.title || source.name || (url ? new URL(url).hostname : `Source ${index + 1}`);
              const host = url ? (() => {
                try {
                  return new URL(url).hostname.replace(/^www\./, "");
                } catch {
                  return url;
                }
              })() : null;

              let faviconUrl;
              if (url) {
                try {
                  const domain = new URL(url).hostname;
                  faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
                } catch {}
              }

              return (
                <li key={source.id || `source-${index}`}>
                  {url ? (
                    <a href={url} target="_blank" rel="noopener noreferrer">
                      {title}
                    </a>
                  ) : (
                    <span className="source-title">{title}</span>
                  )}
                  <div className="source-meta">
                    {faviconUrl && (
                      <img
                        src={faviconUrl}
                        alt=""
                        width={16}
                        height={16}
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    )}
                    {host && <span className="source-host">{host}</span>}
                  </div>
                  {source.snippet && <p className="source-snippet">{source.snippet}</p>}
                </li>
              );
            })}
          </ul>
      </div>
    </div>
  );
};
