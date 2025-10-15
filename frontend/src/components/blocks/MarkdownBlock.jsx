import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./CodeBlock.jsx";

const MarkdownBlock = ({ text }) => {
  if (!text) return null;

  return (
    <ReactMarkdown
      className="markdown-content"
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const code = String(children ?? "").replace(/\n$/, "");

          if (!inline && match) {
            return (
              <CodeBlock
                language={match[1]}
                code={code}
                {...props}
              />
            );
          }

          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        table({ children }) {
          return (
            <div className="markdown-table-wrapper">
              <table>{children}</table>
            </div>
          );
        },
        th({ children }) {
          return <th className="markdown-table-header">{children}</th>;
        },
        td({ children }) {
          return <td className="markdown-table-cell">{children}</td>;
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
};

export { MarkdownBlock };
