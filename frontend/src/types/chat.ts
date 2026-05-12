export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
}

export interface ModelInfo {
  name: string;
  description: string;
  provider: string;
}

export interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
  model?: string;
  createdAt: Date;
}
