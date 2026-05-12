"use client";

import { useState, useCallback } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { Sidebar } from "@/components/layout/Sidebar";
import { Session } from "@/types/chat";

const PROFESSIONAL_QUICK = [
  "藏医有哪些特色疗法？",
  "羌族医药的历史渊源",
  "彝族药方的特点",
];

const LIVING_QUICK = [
  "今天天气不错，适合做什么？",
  "推荐一些健康的饮食习惯",
  "如何缓解工作压力？",
];

export default function ChatPage() {
  const { messages, isStreaming, isWaiting, sendMessage, stopGeneration, clearMessages, setMessagesDirectly } =
    useChat();
  const [selectedModel, setSelectedModel] = useState("专业模型");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);

  // 保存当前会话
  const saveCurrentSession = useCallback(() => {
    if (messages.length === 0) return;
    const title = messages.find((m) => m.role === "user")?.content.slice(0, 20) || "新对话";
    const session: Session = {
      id: currentSessionId || Date.now().toString(),
      title,
      messages: [...messages],
      model: selectedModel,
      createdAt: new Date(),
    };
    setSessions((prev) => {
      const idx = prev.findIndex((s) => s.id === session.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = session;
        return next;
      }
      return [session, ...prev];
    });
    return session.id;
  }, [messages, currentSessionId, selectedModel]);

  // 新建对话
  const handleNewSession = () => {
    saveCurrentSession();
    clearMessages();
    setCurrentSessionId(null);
  };

  // 切换会话
  const handleSelectSession = (id: string) => {
    saveCurrentSession();
    const session = sessions.find((s) => s.id === id);
    if (session) {
      setCurrentSessionId(id);
      setSelectedModel(session.model || "专业模型");
      setMessagesDirectly(session.messages);
    }
  };

  // 切换模型
  const handleSwitchModel = async (model: string) => {
    if (model === selectedModel || switching) return;
    setSwitching(true);
    try {
      const { switchModel } = await import("@/lib/api");
      await switchModel(model);
      saveCurrentSession();
      setSelectedModel(model);
      clearMessages();
      setCurrentSessionId(null);
    } catch (err) {
      console.error("Model switch failed:", err);
    } finally {
      setSwitching(false);
    }
  };

  const quickQuestions = selectedModel === "专业模型" ? PROFESSIONAL_QUICK : LIVING_QUICK;
  const welcomeSubtext =
    selectedModel === "专业模型"
      ? "传承千年的民族医药智慧，以现代 AI 技术为您答疑解惑。\n支持藏族、羌族、彝族医药知识问答。"
      : "我是您的生活助手，可以聊天、提建议、回答日常问题。\n有什么想聊的尽管问我~";

  return (
    <div className="flex h-screen bg-clay-50">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        selectedModel={selectedModel}
        switching={switching}
        onSelectSession={handleSelectSession}
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
                  {selectedModel === "专业模型" ? "民医智问" : "生活助手"}
                </h2>
                <p className="text-clay-400 text-center max-w-md whitespace-pre-line">
                  {welcomeSubtext}
                </p>
                <div className="flex gap-3 mt-8 flex-wrap justify-center">
                  {quickQuestions.map((q) => (
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
                <ChatMessage
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  isWaiting={isWaiting && i === messages.length - 1 && msg.role === "assistant"}
                />
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
