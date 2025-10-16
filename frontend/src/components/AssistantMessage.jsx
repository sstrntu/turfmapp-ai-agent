import React from "react";
import { BlockRenderer } from "./BlockRenderer.jsx";
import { ReasoningPanel } from "./ReasoningPanel.jsx";
import { SourcesPanel } from "./SourcesPanel.jsx";

const isNonEmptyString = (value) =>
  typeof value === "string" && value.trim().length > 0;

const appendIfText = (buffer, text) => {
  if (isNonEmptyString(text)) {
    buffer.push(text.trim());
  }
};

const normaliseReasoning = (incoming = []) => {
  if (!incoming) return [];
  const array = Array.isArray(incoming) ? incoming : [incoming];
  return array
    .map((item) =>
      typeof item === "string" ? item.trim() : JSON.stringify(item, null, 2),
    )
    .filter((entry) => entry.length > 0);
};

const convertToolCallToBlock = (part, index) => {
  const base = {
    id: part.toolCallId || `tool-${index}`,
    type: "tool-call",
    toolName: part.toolName,
    args: part.args,
    argsText: part.argsText,
    result: part.result,
    isError: part.isError,
  };

  if (!part.result) {
    return base;
  }

  const name = (part.toolName || "").toLowerCase();

  if (name.includes("weather")) {
    return {
      ...base,
      type: "weather",
      title: part.args?.location || "Weather",
      data: part.result,
    };
  }

  if (name.includes("search")) {
    return {
      ...base,
      type: "search-results",
      title: part.result?.title || "Search results",
      results: part.result?.results || part.result?.items || [],
    };
  }

  if (typeof part.result === "string" && part.result.trim().length > 0) {
    return {
      ...base,
      type: "markdown",
      text: part.result,
    };
  }

  if (part.result?.markdown) {
    return {
      ...base,
      type: "markdown",
      text: part.result.markdown,
    };
  }

  if (part.result?.code) {
    return {
      ...base,
      type: "code",
      language: part.result.language || part.result.lang,
      code: part.result.code,
    };
  }

  if (
    Array.isArray(part.result?.pairs) ||
    Array.isArray(part.result?.rows) ||
    Array.isArray(part.result?.headers)
  ) {
    return {
      ...base,
      type: part.result?.pairs ? "key-value" : "table",
      title: part.result?.title,
      pairs: part.result?.pairs,
      headers: part.result?.headers,
      rows: part.result?.rows,
    };
  }

  return base;
};

const buildAssistantPresentation = (message) => {
  const textSegments = [];
  const reasoningSegments = [];
  const sourceSegments = [];
  const blockSegments = [];

  (message.content || []).forEach((part, index) => {
    if (!part) return;
    switch (part.type) {
      case "text":
        appendIfText(textSegments, part.text);
        break;
      case "reasoning":
        appendIfText(reasoningSegments, part.text);
        break;
      case "source":
        sourceSegments.push({
          id: part.id || `src-${index}`,
          title: part.title || part.url || `Source ${index + 1}`,
          url: part.url,
        });
        break;
      case "tool-call":
        blockSegments.push(convertToolCallToBlock(part, index));
        break;
      default:
        if (part.text) {
          appendIfText(textSegments, part.text);
        }
    }
  });

  const metadata = message.metadata?.custom ?? {};

  const primaryBlocks = [];
  if (textSegments.length > 0) {
    primaryBlocks.push({
      id: `${message.id}-markdown`,
      type: "markdown",
      text: textSegments.join("\n\n"),
    });
  }

  primaryBlocks.push(...blockSegments);

  const metadataBlocks = Array.isArray(metadata.blocks) ? metadata.blocks : [];
  const mergedBlocks = [
    ...primaryBlocks,
    ...metadataBlocks.map((block, index) => ({
      id: block.id || `${message.id}-meta-${index}`,
      ...block,
    })),
  ];

  const mergedReasoning = [
    ...reasoningSegments,
    ...normaliseReasoning(metadata.reasoning),
  ];

  const mergedSources =
    sourceSegments.length > 0
      ? sourceSegments
      : Array.isArray(metadata.sources)
      ? metadata.sources
      : [];

  return {
    blocks: mergedBlocks,
    reasoning: normaliseReasoning(mergedReasoning),
    sources: mergedSources,
  };
};

export const AssistantMessage = ({ message }) => {
  const { blocks, reasoning, sources } = React.useMemo(
    () => buildAssistantPresentation(message),
    [message],
  );

  const isRunning = message.status?.type === "running";

  return (
    <div className="assistant-message message-appear">
      {isRunning && (
        <div className="assistant-status-pulse" aria-live="polite">
          Thinking…
        </div>
      )}

      <div className="assistant-content">
        {blocks.length === 0 ? (
          !isRunning && <p className="markdown-content">I didn&apos;t receive any content.</p>
        ) : (
          blocks.map((block) => (
            <BlockRenderer key={block.id || `${message.id}-${block.type}`} block={block} />
          ))
        )}
      </div>

      <ReasoningPanel reasoning={reasoning} />
      <SourcesPanel sources={sources} />
    </div>
  );
};
