"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

interface StreamingTextProps {
  text: string;
  isStreaming?: boolean;
}

export function StreamingText({ text, isStreaming = false }: StreamingTextProps) {
  const [visibleText, setVisibleText] = useState(isStreaming ? "" : text);

  useEffect(() => {
    if (!isStreaming) {
      setVisibleText(text);
      return;
    }

    setVisibleText("");
    let index = 0;
    const timer = window.setInterval(() => {
      index += 3;
      setVisibleText(text.slice(0, index));
      if (index >= text.length) {
        window.clearInterval(timer);
      }
    }, 18);

    return () => window.clearInterval(timer);
  }, [isStreaming, text]);

  return (
    <div className="relative">
      <ReactMarkdown
        components={{
          h2: ({ children }) => (
            <h2 className="mb-2 mt-4 text-lg font-semibold text-amber-50">
              {children}
            </h2>
          ),
          p: ({ children }) => <p className="my-2">{children}</p>,
          ul: ({ children }) => (
            <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-stone-50">{children}</strong>
          ),
        }}
      >
        {visibleText}
      </ReactMarkdown>
      {isStreaming && visibleText.length < text.length ? (
        <span className="ml-0.5 inline-block h-4 w-1 animate-pulse rounded-full bg-teal-300 align-[-2px]" />
      ) : null}
    </div>
  );
}
