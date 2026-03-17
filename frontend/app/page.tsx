"use client";

import { useState, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import MetricsPanel from "@/components/MetricsPanel";
import ChatWindow from "@/components/ChatWindow";
import { Message, Metrics } from "@/lib/types";

const INITIAL_METRICS: Metrics = {
  turnNum: 0,
  avgProductScore: 0,
  totalTokens: 0,
  episodicChunks: 0,
  preferenceChunks: 0,
  factsExtracted: 0,
  summaryCreated: false,
  scores: [],
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [metrics, setMetrics] = useState<Metrics>(INITIAL_METRICS);
  const [sessionId, setSessionId] = useState<string>(() => uuidv4());
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, message: text }),
        }
      );

      if (!res.ok) throw new Error("API error");
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
      setMetrics({
        turnNum: data.metrics.turn_num + 1,
        avgProductScore: data.metrics.avg_product_score,
        totalTokens: data.metrics.total_tokens,
        episodicChunks: data.metrics.episodic_chunks,
        preferenceChunks: data.metrics.preference_chunks,
        factsExtracted: data.metrics.facts_extracted,
        summaryCreated: data.metrics.summary_created,
        scores: data.metrics.scores,
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Is the backend running?",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const resetSession = async () => {
    const newId = uuidv4();
    await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/session/${sessionId}`,
      { method: "DELETE" }
    ).catch(() => {});
    setSessionId(newId);
    setMessages([]);
    setMetrics(INITIAL_METRICS);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0a0a0f" }}>
      {/* Header */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 24px",
        background: "#12121a",
        borderBottom: "1px solid #2a2a3a",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 22 }}>🛒</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 17, color: "#e2e8f0", letterSpacing: "-0.3px" }}>
              ContextShop
            </div>
            <div style={{ fontSize: 11, color: "#64748b" }}>
              Retail AI · Powered by Qdrant Context Engineering
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{
            fontSize: 11, color: "#64748b",
            background: "#1a1a26", padding: "3px 8px",
            borderRadius: 4, fontFamily: "monospace",
          }}>
            {sessionId.slice(0, 8)}
          </span>
          <button
            onClick={resetSession}
            style={{
              fontSize: 12, color: "#94a3b8", cursor: "pointer",
              background: "#1a1a26", border: "1px solid #2a2a3a",
              borderRadius: 6, padding: "5px 12px",
            }}
          >
            New Session
          </button>
        </div>
      </header>

      {/* Body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <ChatWindow messages={messages} loading={loading} onSend={sendMessage} />
        <MetricsPanel metrics={metrics} />
      </div>
    </div>
  );
}
