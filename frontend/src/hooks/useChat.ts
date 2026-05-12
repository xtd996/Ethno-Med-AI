"use client";

import { useState, useCallback, useRef } from "react";
import { ChatMessage } from "@/types/chat";
import { createChatStream } from "@/lib/api";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || isStreaming) return;

      const userMessage: ChatMessage = { role: "user", content };
      const newMessages = [...messages, userMessage];
      setMessages(newMessages);
      setIsStreaming(true);

      let assistantContent = "";
      const assistantMessage: ChatMessage = { role: "assistant", content: "" };
      setMessages([...newMessages, assistantMessage]);

      abortRef.current = createChatStream(
        newMessages,
        (token) => {
          assistantContent += token;
          setMessages([
            ...newMessages,
            { role: "assistant", content: assistantContent },
          ]);
        },
        () => {
          setIsStreaming(false);
          abortRef.current = null;
        },
        (error) => {
          setMessages([
            ...newMessages,
            { role: "assistant", content: `错误：${error}` },
          ]);
          setIsStreaming(false);
          abortRef.current = null;
        }
      );
    },
    [messages, isStreaming]
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsStreaming(false);
  }, []);

  return { messages, isStreaming, sendMessage, stopGeneration, clearMessages };
}
