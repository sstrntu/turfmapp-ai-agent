import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { coldarkDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const languageLabel = (lang) => {
  if (!lang) return "text";
  return lang.toLowerCase();
};

export const CodeBlock = ({ code, language = "text" }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.warn("Unable to copy snippet", err);
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-language">{languageLabel(language)}</span>
        <button
          type="button"
          className="copy-code-btn"
          onClick={handleCopy}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={coldarkDark}
        customStyle={{
          background: "transparent",
          margin: 0,
          padding: "16px",
        }}
        wrapLines
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
};
