import React from "react";
import { MarkdownBlock } from "./blocks/MarkdownBlock.jsx";
import { CodeBlock } from "./blocks/CodeBlock.jsx";
import { WeatherBlock } from "./blocks/WeatherBlock.jsx";
import { TableBlock } from "./blocks/TableBlock.jsx";
import { SearchResultsBlock } from "./blocks/SearchResultsBlock.jsx";
import { KeyValueBlock } from "./blocks/KeyValueBlock.jsx";

const renderCode = (block) => (
  <CodeBlock code={block.code || ""} language={block.language || block.lang || "text"} />
);

const renderKeyValueFromObject = (block) => {
  const entries = Object.entries(block.data || {}).map(([label, value]) => ({
    label,
    value: typeof value === "object" ? JSON.stringify(value, null, 2) : String(value),
  }));

  return <KeyValueBlock title={block.title} pairs={entries} />;
};

const renderToolFallback = (block) => {
  return (
    <div className="assistant-widget tool-response-widget">
      <div className="widget-title">{block.title || block.toolName || "Tool response"}</div>
      <pre className="tool-response">
        {JSON.stringify(
          {
            args: block.args ?? block.parameters,
            result: block.result ?? block.data,
            error: block.isError ?? false,
          },
          null,
          2,
        )}
      </pre>
    </div>
  );
};

export const BlockRenderer = ({ block }) => {
  if (!block) return null;

  switch (block.type) {
    case "markdown":
    case "text":
      return <MarkdownBlock text={block.text || ""} />;
    case "code":
      return renderCode(block);
    case "table":
      return (
        <TableBlock
          title={block.title}
          headers={block.headers || block.columns || []}
          rows={block.rows || []}
        />
      );
    case "weather":
      return <WeatherBlock data={block.data || block} title={block.title} />;
    case "search-results":
    case "web-search":
      return (
        <SearchResultsBlock
          title={block.title}
          results={block.results || block.items || []}
        />
      );
    case "key-value":
      return <KeyValueBlock title={block.title} pairs={block.pairs || []} />;
    case "object":
      return renderKeyValueFromObject(block);
    case "tool-call":
    default:
      return renderToolFallback(block);
  }
};
