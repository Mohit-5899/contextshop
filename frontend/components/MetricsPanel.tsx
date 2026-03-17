"use client";

import { Metrics } from "@/lib/types";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Props { metrics: Metrics }

function ScoreBadge({ score }: { score: number }) {
  const color = score > 0.4 ? "#10b981" : score > 0.3 ? "#f59e0b" : "#64748b";
  return (
    <div style={{
      fontSize: 28, fontWeight: 700, color,
      fontVariantNumeric: "tabular-nums",
    }}>
      {score > 0 ? score.toFixed(3) : "—"}
    </div>
  );
}

function MemoryBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "#94a3b8" }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color }}>{value}</span>
      </div>
      <div style={{ height: 4, background: "#2a2a3a", borderRadius: 2 }}>
        <div style={{
          height: "100%", width: `${Math.min(value * 20, 100)}%`,
          background: color, borderRadius: 2,
          transition: "width 0.5s ease",
        }} />
      </div>
    </div>
  );
}

export default function MetricsPanel({ metrics }: Props) {
  const chartData = metrics.scores.map((s, i) => ({ turn: i, score: s }));
  const coldScore = metrics.scores[0] ?? 0;
  const warmScore = metrics.scores[metrics.scores.length - 1] ?? 0;
  const improvement = warmScore - coldScore;

  return (
    <div style={{
      width: 300,
      flexShrink: 0,
      background: "#0d0d15",
      display: "flex",
      flexDirection: "column",
      overflowY: "auto",
      padding: "20px 16px",
      gap: 20,
    }}>
      {/* Title */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#7c3aed", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Context Engine
        </div>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>Live metrics</div>
      </div>

      {/* Retrieval Score */}
      <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "14px 16px" }}>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>RETRIEVAL SCORE</div>
        <ScoreBadge score={metrics.avgProductScore} />
        <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>latest query</div>
      </div>

      {/* Turn + Tokens */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "12px 14px" }}>
          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>TURNS</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0" }}>{metrics.turnNum}</div>
        </div>
        <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "12px 14px" }}>
          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>TOKENS</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0" }}>{metrics.totalTokens || "—"}</div>
        </div>
      </div>

      {/* Memory */}
      <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "14px 16px" }}>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 12 }}>MEMORY GROWTH</div>
        <MemoryBar label="Episodic summaries" value={metrics.episodicChunks} color="#7c3aed" />
        <MemoryBar label="Preference facts" value={metrics.preferenceChunks} color="#06b6d4" />
        {metrics.factsExtracted > 0 && (
          <div style={{
            marginTop: 8, fontSize: 11, color: "#10b981",
            background: "#10b98115", border: "1px solid #10b98130",
            borderRadius: 6, padding: "4px 8px", display: "inline-block",
          }}>
            +{metrics.factsExtracted} facts learned
          </div>
        )}
        {metrics.summaryCreated && (
          <div style={{
            marginTop: 6, fontSize: 11, color: "#7c3aed",
            background: "#7c3aed15", border: "1px solid #7c3aed30",
            borderRadius: 6, padding: "4px 8px", display: "inline-block",
          }}>
            ✦ Memory compressed
          </div>
        )}
      </div>

      {/* Score chart */}
      {chartData.length > 1 && (
        <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 12 }}>SCORE PROGRESSION</div>
          <ResponsiveContainer width="100%" height={90}>
            <LineChart data={chartData}>
              <XAxis dataKey="turn" tick={{ fontSize: 10, fill: "#64748b" }} />
              <YAxis domain={[0, 0.6]} tick={{ fontSize: 10, fill: "#64748b" }} width={30} />
              <Tooltip
                contentStyle={{ background: "#1a1a26", border: "1px solid #2a2a3a", borderRadius: 6, fontSize: 11 }}
                labelFormatter={(v) => `Turn ${v}`}
                formatter={(v) => [Number(v).toFixed(3), "Score"]}
              />
              <Line
                type="monotone" dataKey="score" stroke="#7c3aed"
                strokeWidth={2} dot={{ r: 3, fill: "#7c3aed" }}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cold vs Warm */}
      {metrics.scores.length >= 2 && (
        <div style={{ background: "#12121a", border: "1px solid #2a2a3a", borderRadius: 10, padding: "14px 16px" }}>
          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 10 }}>COLD → WARM</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "#64748b" }}>Cold</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#94a3b8" }}>{coldScore.toFixed(3)}</div>
            </div>
            <div style={{ fontSize: 18, color: "#2a2a3a" }}>→</div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "#64748b" }}>Warm</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#10b981" }}>{warmScore.toFixed(3)}</div>
            </div>
            <div style={{
              fontSize: 13, fontWeight: 700,
              color: improvement >= 0 ? "#10b981" : "#ef4444",
            }}>
              {improvement >= 0 ? "+" : ""}{(improvement * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {metrics.turnNum === 0 && (
        <div style={{ color: "#64748b", fontSize: 12, textAlign: "center", padding: "20px 0" }}>
          Start chatting to see context metrics update in real time.
        </div>
      )}
    </div>
  );
}
