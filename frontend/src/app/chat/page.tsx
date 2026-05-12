"use client";

import { useState } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sidebar } from "@/components/layout/Sidebar";
import { Session } from "@/types/chat";

export default function ChatPage() {
  const { messages, isStreaming, sendMessage, stopGeneration, clearMessages } =
    useChat();
  const [selectedModel, setSelectedModel] = useState("专业模型");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const handleNewSession = () => {
    clearMessages();
    setCurrentSessionId(null);
  };

  const handleSwitchModel = async (model: string) => {
    try {
      const { switchModel } = await import("@/lib/api");
      await switchModel(model);
      setSelectedModel(model);
    } catch (err) {
      console.error("Model switch failed:", err);
    }
  };

  return (
    <div className="flex h-screen bg-clay-50">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        selectedModel={selectedModel}
        onSelectSession={setCurrentSessionId}
        onNewSession={handleNewSession}
        onSwitchModel={handleSwitchModel}
      />

      <main className="flex-1 flex flex-col">
        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[60vh]">
                <div className="w-16 h-16 rounded-full bg-celadon-100 flex items-center justify-center mb-6">
                  <span className="text-celadon-600 text-2xl font-display">
                    医
                  </span>
                </div>
                <h2 className="font-display text-2xl text-clay-700 mb-2">
                  民医智问
                </h2>
                <p className="text-clay-400 text-center max-w-md">
                  传承千年的民族医药智慧，以现代 AI 技术为您答疑解惑。
                  <br />
                  支持藏族、羌族、彝族医药知识问答。
                </p>
                <div className="flex gap-3 mt-8">
                  {[
                    "藏医有哪些特色疗法？",
                    "羌族医药的历史渊源",
                    "彝族药方的特点",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="px-4 py-2 rounded-lg bg-clay-100/80 text-clay-600 text-sm hover:bg-clay-200 transition-colors duration-200"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <ChatMessage key={i} role={msg.role} content={msg.content} />
              ))
            )}
          </div>
        </div>

        {/* 输入区域 */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopGeneration}
          isStreaming={isStreaming}
        />
      </main>
    </div>
  );
}
