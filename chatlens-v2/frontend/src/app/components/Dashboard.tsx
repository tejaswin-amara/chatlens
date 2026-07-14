"use client";

import type { ChatStats } from "../types";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface DashboardProps {
  chatStats: ChatStats | null;
  loading: boolean;
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const chartOptions = (title: string) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    title: {
      display: true,
      text: title,
      color: "#71717a",
      font: { size: 12, weight: "normal" as const },
    },
    tooltip: {
      backgroundColor: "rgba(10,10,15,0.9)",
      borderColor: "rgba(255,255,255,0.08)",
      borderWidth: 1,
      titleColor: "#fafafa",
      bodyColor: "#e4e4e7",
    },
  },
  scales: {
    x: {
      ticks: { color: "#71717a", font: { size: 10 } },
      grid: { color: "rgba(255,255,255,0.04)" },
      border: { color: "rgba(255,255,255,0.08)" },
    },
    y: {
      ticks: { color: "#71717a", font: { size: 10 } },
      grid: { color: "rgba(255,255,255,0.04)" },
      border: { color: "rgba(255,255,255,0.08)" },
    },
  },
});

function SkeletonCard() {
  return (
    <div className="bg-brand-card border border-brand-border rounded-brand p-5 animate-pulse">
      <div className="h-7 w-20 bg-brand-border/50 rounded mb-2" />
      <div className="h-3 w-24 bg-brand-border/50 rounded" />
    </div>
  );
}

function SkeletonChart() {
  return (
    <div className="bg-brand-card border border-brand-border rounded-brand p-5 h-64 animate-pulse">
      <div className="h-3 w-32 bg-brand-border/50 rounded mb-4" />
      <div className="flex items-end gap-1 h-40">
        {[40, 60, 30, 80, 50, 70, 90, 40, 50, 60, 80, 50].map((h, i) => (
          <div
            key={i}
            className="flex-1 bg-brand-border/30 rounded-sm"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function Dashboard({ chatStats, loading }: DashboardProps) {
  if (loading || !chatStats) {
    return (
      <div className="p-6 space-y-6 animate-fade-in">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonChart />
          <SkeletonChart />
        </div>
      </div>
    );
  }

  const avgWords = chatStats.total_messages > 0
    ? (chatStats.total_words / chatStats.total_messages).toFixed(1)
    : "0";

  const stats = [
    { label: "Total Messages", value: chatStats.total_messages.toLocaleString() },
    { label: "Total Words", value: chatStats.total_words.toLocaleString() },
    { label: "Avg Words / Msg", value: avgWords },
    { label: "Top Senders", value: chatStats.top_senders.length.toString() },
  ];

  const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const hourData = hourLabels.map((_, i) => chatStats.activity_by_hour[String(i)] ?? 0);

  const dayData = DAY_LABELS.map((d) => chatStats.activity_by_day[d] ?? 0);

  const awards = chatStats.awards ? Object.entries(chatStats.awards) : [];

  return (
    <div className="p-6 space-y-6 animate-fade-in overflow-y-auto">
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-brand-card border border-brand-border rounded-brand p-5"
          >
            <div className="text-2xl font-bold text-brand-accent">{s.value}</div>
            <div className="text-[0.7rem] uppercase tracking-wider text-brand-text-dim mt-1">
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Awards */}
      {awards.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {awards.map(([title, winner]) => (
            <div
              key={title}
              className="rounded-brand border border-brand-accent/30 bg-gradient-to-br from-brand-accent/10 to-transparent p-4"
            >
              <div className="text-sm font-medium text-brand-text-bright">{title}</div>
              <div className="text-[0.8rem] text-brand-text-dim mt-1">{winner}</div>
            </div>
          ))}
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-brand-card border border-brand-border rounded-brand p-5 h-64">
          <Bar
            data={{
              labels: hourLabels,
              datasets: [{
                data: hourData,
                backgroundColor: "rgba(0,212,170,0.5)",
                borderRadius: 3,
              }],
            }}
            options={chartOptions("Activity by Hour")}
          />
        </div>
        <div className="bg-brand-card border border-brand-border rounded-brand p-5 h-64">
          <Bar
            data={{
              labels: DAY_LABELS,
              datasets: [{
                data: dayData,
                backgroundColor: "rgba(42,171,238,0.5)",
                borderRadius: 3,
              }],
            }}
            options={chartOptions("Activity by Day")}
          />
        </div>
      </div>

      {/* Top Contributors */}
      {chatStats.top_senders.length > 0 && (
        <div className="bg-brand-card border border-brand-border rounded-brand p-5">
          <h3 className="text-[0.75rem] uppercase tracking-wider text-brand-text-dim mb-3">
            Top Contributors
          </h3>
          <div className="space-y-1.5">
            {chatStats.top_senders.map((s, i) => (
              <div
                key={s.name}
                className="flex items-center justify-between rounded-brand-sm px-3 py-2 bg-white/5"
              >
                <span className="text-sm text-brand-text">
                  <span className="text-brand-text-dim mr-2 text-xs">{i + 1}.</span>
                  {s.name}
                </span>
                <span className="text-sm text-brand-accent font-medium">
                  {s.count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
