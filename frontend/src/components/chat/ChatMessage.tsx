"use client";

import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  isWaiting?: boolean;
}

export function ChatMessage({ role, content, isWaiting }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 animate-fade-in`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-celadon-200 flex items-center justify-center mr-3 mt-1 flex-shrink-0">
          <span className="text-celadon-700 text-sm font-display">医</span>
        </div>
      )}
      <div
        className={`max-w-[70%] ${
          isUser
            ? "bg-clay-500 text-white rounded-2xl rounded-br-md px-5 py-3"
            : "bg-clay-50/80 backdrop-blur-sm border border-clay-100 rounded-2xl rounded-bl-md px-5 py-3 text-ink-700"
        }`}
      >
        {isUser ? (
          <p className="leading-relaxed">{content}</p>
        ) : isWaiting && !content ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="w-2 h-2 rounded-full bg-celadon-400 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 rounded-full bg-celadon-400 animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 rounded-full bg-celadon-400 animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        ) : (
          <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-ink-800 prose-p:text-ink-600 prose-strong:text-ink-700 prose-code:bg-clay-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
