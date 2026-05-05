"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { adviceApi } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { format } from "date-fns";
import {
  ArrowLeft,
  Send,
  Loader2,
  Bot,
  User,
  Sparkles,
  RefreshCw,
  ChevronRight,
} from "lucide-react";

// ==========================================
// Types
// ==========================================

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  streaming?: boolean;
}

interface QuickPrompt {
  label: string;
  prompt: string;
  emoji: string;
}

// ==========================================
// Constants
// ==========================================

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    emoji: "📊",
    label: "Weekly summary",
    prompt: "Give me a summary of my eating habits this week and what I should improve.",
  },
  {
    emoji: "💪",
    label: "Protein tips",
    prompt: "Am I getting enough protein? How can I increase my protein intake with healthy foods?",
  },
  {
    emoji: "⚖️",
    label: "Calorie balance",
    prompt: "How is my calorie intake compared to my goal? Am I on track?",
  },
  {
    emoji: "🥗",
    label: "Meal suggestions",
    prompt: "Based on what I have been eating, what meals would you suggest to balance my nutrition?",
  },
  {
    emoji: "😴",
    label: "Energy levels",
    prompt: "Could my diet be affecting my energy levels? What foods should I add or avoid?",
  },
  {
    emoji: "🎯",
    label: "Goal check",
    prompt: "Am I making progress toward my nutrition goals? What should I focus on this week?",
  },
];

// ==========================================
// Message bubble
// ==========================================

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`
          w-8 h-8 rounded-full shrink-0 flex items-center justify-center
          ${isUser ? "bg-primary-600" : "bg-gradient-to-br from-purple-500 to-indigo-600"}
        `}
      >
        {isUser
          ? <User className="w-4 h-4 text-white" />
          : <Bot className="w-4 h-4 text-white" />
        }
      </div>

      {/* Bubble */}
      <div
        className={`
          max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? "bg-primary-600 text-white rounded-tr-sm"
            : "bg-white border border-gray-100 text-gray-700 rounded-tl-sm"
          }
        `}
      >
        {/* Streaming indicator */}
        {message.streaming && (
          <span className="inline-flex gap-1 mb-1">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
        )}

        {/* Content */}
        <p className="whitespace-pre-line">{message.content}</p>

        {/* Timestamp */}
        <p
          className={`text-xs mt-1.5 ${
            isUser ? "text-primary-200" : "text-gray-400"
          }`}
        >
          {format(message.timestamp, "h:mm a")}
        </p>
      </div>
    </div>
  );
}

// ==========================================
// Quick prompt chip
// ==========================================

function QuickPromptChip({
  prompt,
  onClick,
  disabled,
}: {
  prompt: QuickPrompt;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 hover:border-primary-300 hover:bg-primary-50 hover:text-primary-600 transition-all disabled:opacity-50 disabled:pointer-events-none shrink-0"
    >
      <span>{prompt.emoji}</span>
      <span className="font-medium whitespace-nowrap">{prompt.label}</span>
      <ChevronRight className="w-3.5 h-3.5 opacity-50" />
    </button>
  );
}

// ==========================================
// Empty state
// ==========================================

function EmptyState({ onPromptClick }: { onPromptClick: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center py-8 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-100 to-indigo-100 flex items-center justify-center mb-4">
        <Sparkles className="w-8 h-8 text-purple-500" />
      </div>
      <h2 className="font-bold text-gray-700 text-lg mb-1">
        AI Nutrition Advisor
      </h2>
      <p className="text-sm text-gray-400 max-w-xs leading-relaxed mb-6">
        Ask me anything about your diet, nutrition goals, or get personalized
        meal recommendations based on your food history.
      </p>

      {/* Suggestion grid */}
      <div className="w-full grid grid-cols-1 gap-2 max-w-sm">
        {QUICK_PROMPTS.slice(0, 4).map((p) => (
          <button
            key={p.label}
            onClick={() => onPromptClick(p.prompt)}
            className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-100 rounded-xl text-left hover:border-primary-200 hover:bg-primary-50 transition-all group"
          >
            <span className="text-xl">{p.emoji}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 group-hover:text-primary-600">
                {p.label}
              </p>
              <p className="text-xs text-gray-400 truncate">{p.prompt}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-primary-400 shrink-0" />
          </button>
        ))}
      </div>
    </div>
  );
}

// ==========================================
// Main page
// ==========================================

export default function AdvicePage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [dateRange, setDateRange] = useState(7);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamingIdRef = useRef<string | null>(null);

  // ==========================================
  // Auth guard
  // ==========================================

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/login");
    }
  }, [router]);

  // ==========================================
  // Auto scroll
  // ==========================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ==========================================
  // Auto resize textarea
  // ==========================================

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  // ==========================================
  // Send message
  // ==========================================

  const sendMessage = async (text?: string) => {
    const content = (text || input).trim();
    if (!content || streaming) return;

    setInput("");
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    // Add user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Add streaming assistant placeholder
    const assistantId = crypto.randomUUID();
    streamingIdRef.current = assistantId;

    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      streaming: true,
    };
    setMessages((prev) => [...prev, assistantMsg]);
    setStreaming(true);

    try {
      // Use streaming endpoint
      const eventSource = adviceApi.streamAdvice(content, dateRange);
      let accumulated = "";

      eventSource.onmessage = (event) => {
        if (event.data === "[DONE]") {
          eventSource.close();
          setStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, streaming: false }
                : m
            )
          );
          return;
        }

        try {
          const parsed = JSON.parse(event.data);
          accumulated += parsed.text;

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: accumulated }
                : m
            )
          );
        } catch {
          // Ignore parse errors
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setStreaming(false);

        // Fallback to non-streaming
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: accumulated || "Sorry, I could not generate a response. Please try again.",
                  streaming: false,
                }
              : m
          )
        );
      };

    } catch {
      setStreaming(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: "Something went wrong. Please try again.",
                streaming: false,
              }
            : m
        )
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setStreaming(false);
  };

  // ==========================================
  // Render
  // ==========================================

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">

      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-400 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-base font-bold text-gray-800">
              AI Nutrition Advisor
            </h1>
            <p className="text-xs text-gray-400">Powered by Claude AI</p>
          </div>

          {/* Date range selector */}
          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 text-gray-600 bg-white focus:outline-none focus:ring-2 focus:ring-primary-300"
          >
            <option value={3}>Last 3 days</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>

          {/* Clear chat */}
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-400 transition-colors"
              title="Clear chat"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-4 space-y-4 overflow-y-auto pb-48">
        {messages.length === 0 ? (
          <EmptyState onPromptClick={sendMessage} />
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Bottom input area */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100">
        <div className="max-w-lg mx-auto px-4 py-3">

          {/* Quick prompts scroll */}
          {messages.length === 0 && (
            <div className="flex gap-2 overflow-x-auto pb-2 mb-2 scrollbar-hide">
              {QUICK_PROMPTS.map((p) => (
                <QuickPromptChip
                  key={p.label}
                  prompt={p}
                  onClick={() => sendMessage(p.prompt)}
                  disabled={streaming}
                />
              ))}
            </div>
          )}

          {/* Input row */}
          <div className="flex items-end gap-2">
            <div className="flex-1 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-2.5 focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your nutrition..."
                rows={1}
                disabled={streaming}
                className="w-full text-sm text-gray-700 placeholder:text-gray-400 bg-transparent resize-none focus:outline-none max-h-32 disabled:opacity-60"
              />
            </div>

            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || streaming}
              className="w-10 h-10 rounded-2xl bg-primary-600 flex items-center justify-center text-white hover:bg-primary-700 active:scale-95 transition-all disabled:opacity-40 disabled:pointer-events-none shrink-0"
            >
              {streaming
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Send className="w-4 h-4" />
              }
            </button>
          </div>

          <p className="text-xs text-gray-400 text-center mt-2">
            Advice is based on your last {dateRange} days of food logs
          </p>
        </div>
      </div>

    </div>
  );
}