"use client";

import { useEffect, useRef, useState } from "react";
import { Message } from "@/lib/types";

interface Props {
  messages: Message[];
  loading: boolean;
  onSend: (text: string) => void;
}

export default function ChatWindow({ messages, loading, onSend }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      borderRight: "1px solid #2a2a3a",
      overflow: "hidden",
    }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
        {messages.length === 0 && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, opacity: 0.5 }}>
            <div style={{ fontSize: 36 }}>🛒</div>
            <div style={{ color: "#64748b", fontSize: 14, textAlign: "center", maxWidth: 300 }}>
              Ask about sports & outdoor products.<br />
              Watch the context engine learn as you chat.
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            {msg.role === "assistant" && (
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 13, flexShrink: 0, marginRight: 10, marginTop: 2,
              }}>🛒</div>
            )}
            <div style={{
              maxWidth: "72%",
              padding: "10px 14px",
              borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              background: msg.role === "user"
                ? "linear-gradient(135deg, #7c3aed, #6d28d9)"
                : "#1a1a26",
              border: msg.role === "assistant" ? "1px solid #2a2a3a" : "none",
              fontSize: 14,
              lineHeight: 1.6,
              color: "#e2e8f0",
              whiteSpace: "pre-wrap",
            }}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13,
            }}>🛒</div>
            <div style={{ display: "flex", gap: 4, padding: "10px 14px", background: "#1a1a26", border: "1px solid #2a2a3a", borderRadius: "16px 16px 16px 4px" }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 6, height: 6, borderRadius: "50%", background: "#7c3aed",
                  animation: "pulse 1.2s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }} />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{
        padding: "16px 20px",
        borderTop: "1px solid #2a2a3a",
        display: "flex", gap: 10, background: "#0d0d15",
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about sports & outdoor products..."
          disabled={loading}
          style={{
            flex: 1,
            background: "#1a1a26",
            border: "1px solid #2a2a3a",
            borderRadius: 10,
            padding: "10px 14px",
            color: "#e2e8f0",
            fontSize: 14,
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            background: "linear-gradient(135deg, #7c3aed, #6d28d9)",
            border: "none",
            borderRadius: 10,
            width: 42,
            height: 42,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            opacity: loading || !input.trim() ? 0.5 : 1,
            color: "white",
            fontSize: 18,
            flexShrink: 0,
          }}
        >
          ↑
        </button>
      </form>

      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
