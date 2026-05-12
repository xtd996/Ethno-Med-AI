"use client";

import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, onStop, isStreaming, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    if (isStreaming) {
      onStop?.();
      return;
    }
    if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="sticky bottom-0 bg-clay-50/90 backdrop-blur-md border-t border-clay-100 px-6 py-4">
      <div className="max-w-3xl mx-auto flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="请描述您的问题..."
          disabled={disabled || isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-clay-200 bg-white/80 px-4 py-3 text-ink-700 placeholder:text-clay-300 focus:outline-none focus:border-clay-400 focus:ring-2 focus:ring-clay-200 transition-all duration-200"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || (!isStreaming && !input.trim())}
          className={`px-5 py-3 rounded-xl font-medium transition-all duration-200 ${
            isStreaming
              ? "bg-ink-400 text-white hover:bg-ink-500"
              : "bg-clay-500 text-white hover:bg-clay-600 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
        >
          {isStreaming ? "停止" : "发送"}
        </button>
      </div>
      <p className="text-center text-xs text-clay-300 mt-2">
        民医智问 · 内容仅供参考，不构成医疗建议
      </p>
    </div>
  );
}
