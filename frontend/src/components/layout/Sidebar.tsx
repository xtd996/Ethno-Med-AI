"use client";

import { Session } from "@/types/chat";

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  selectedModel: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onSwitchModel: (model: string) => void;
}

export function Sidebar({
  sessions,
  currentSessionId,
  selectedModel,
  onSelectSession,
  onNewSession,
  onSwitchModel,
}: SidebarProps) {
  return (
    <aside className="w-72 h-screen bg-clay-50/60 backdrop-blur-sm border-r border-clay-100 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-clay-100">
        <h1 className="font-display text-xl text-clay-700">民医智问</h1>
        <p className="text-xs text-clay-400 mt-1">Ethno Med AI</p>
      </div>

      {/* 模型切换 */}
      <div className="px-4 py-4 border-b border-clay-100">
        <p className="text-xs text-clay-400 mb-2 px-2">选择模型</p>
        <div className="space-y-2">
          {["专业模型", "生活模型"].map((model) => (
            <button
              key={model}
              onClick={() => onSwitchModel(model)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                selectedModel === model
                  ? "bg-clay-500 text-white shadow-sm"
                  : "text-ink-500 hover:bg-clay-100"
              }`}
            >
              <span className="font-medium">{model}</span>
              <span className="block text-xs mt-0.5 opacity-70">
                {model === "专业模型" ? "民族医药专业问答" : "日常聊天助手"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* 新建对话 */}
      <div className="px-4 py-3">
        <button
          onClick={onNewSession}
          className="w-full px-4 py-2.5 rounded-lg border border-dashed border-clay-300 text-clay-500 text-sm hover:bg-clay-100 hover:border-clay-400 transition-all duration-200"
        >
          + 新建对话
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm mb-1 truncate transition-all duration-200 ${
              currentSessionId === session.id
                ? "bg-clay-200/60 text-clay-700"
                : "text-ink-400 hover:bg-clay-100/60"
            }`}
          >
            {session.title}
          </button>
        ))}
      </div>

      {/* 底部 */}
      <div className="px-6 py-4 border-t border-clay-100">
        <p className="text-xs text-clay-300 text-center">
          少数民族医药 · 藏族 · 羌族 · 彝族
        </p>
      </div>
    </aside>
  );
}
