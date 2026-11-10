"use client";

import React from "react";
import {
  Activity,
  AlertCircle,
  Clock,
  Radio,
  Users,
} from "lucide-react";
import { useLiveStream } from "@/lib/use-live-stream";

interface LiveStreamMonitorProps {
  streamId: string;
}

export function LiveStreamMonitor({ streamId }: LiveStreamMonitorProps) {
  const {
    status,
    viewerCount,
    latencyMs,
    lastHeartbeat,
    events,
    error,
    connect,
    disconnect,
  } = useLiveStream({
    streamId,
    autoConnect: true,
  });

  const statusBadge = {
    connected: {
      bg: "bg-emerald-950/80 border-emerald-800 text-emerald-300",
      dot: "bg-emerald-400 animate-pulse",
      text: "Connected (Heartbeat OK)",
    },
    connecting: {
      bg: "bg-amber-950/80 border-amber-800 text-amber-300",
      dot: "bg-amber-400 animate-ping",
      text: "Connecting...",
    },
    reconnecting: {
      bg: "bg-orange-950/80 border-orange-800 text-orange-300",
      dot: "bg-orange-400 animate-bounce",
      text: "Reconnecting...",
    },
    disconnected: {
      bg: "bg-neutral-900 border-neutral-800 text-neutral-400",
      dot: "bg-neutral-500",
      text: "Disconnected",
    },
  }[status];

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950 p-5 shadow-xl text-neutral-200">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-neutral-900">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 border border-neutral-800 text-emerald-400">
            <Radio className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-100">
              Live Stream Connection Monitor
            </h3>
            <p className="text-xs text-neutral-500 font-mono">Stream: {streamId}</p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${statusBadge.bg}`}
          >
            <span className={`h-2 w-2 rounded-full ${statusBadge.dot}`} />
            <span>{statusBadge.text}</span>
          </div>

          <button
            onClick={status === "connected" ? disconnect : connect}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              status === "connected"
                ? "border border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
                : "bg-emerald-500 text-black hover:bg-emerald-400"
            }`}
          >
            {status === "connected" ? "Disconnect" : "Connect"}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-3 pt-4">
        {/* Latency */}
        <div className="rounded-lg border border-neutral-900 bg-neutral-900/40 p-3">
          <div className="flex items-center gap-1.5 text-xs text-neutral-400">
            <Activity className="h-3.5 w-3.5 text-teal-400" />
            <span>Heartbeat Latency</span>
          </div>
          <div className="mt-1 font-mono text-base font-semibold text-neutral-100">
            {latencyMs !== null ? `${latencyMs} ms` : "—"}
          </div>
        </div>

        {/* Viewers */}
        <div className="rounded-lg border border-neutral-900 bg-neutral-900/40 p-3">
          <div className="flex items-center gap-1.5 text-xs text-neutral-400">
            <Users className="h-3.5 w-3.5 text-blue-400" />
            <span>Active Connections</span>
          </div>
          <div className="mt-1 font-mono text-base font-semibold text-neutral-100">
            {viewerCount}
          </div>
        </div>

        {/* Last Heartbeat */}
        <div className="rounded-lg border border-neutral-900 bg-neutral-900/40 p-3">
          <div className="flex items-center gap-1.5 text-xs text-neutral-400">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            <span>Last Heartbeat</span>
          </div>
          <div className="mt-1 font-mono text-xs font-medium text-neutral-200">
            {lastHeartbeat
              ? lastHeartbeat.toLocaleTimeString()
              : "No heartbeat yet"}
          </div>
        </div>
      </div>

      {/* Error Notice */}
      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-md bg-red-950/60 border border-red-900/60 p-2.5 text-xs text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Event Stream Log */}
      <div className="mt-4">
        <h4 className="text-xs font-medium text-neutral-400 mb-2">
          Live Stream Event Log
        </h4>
        <div className="h-32 overflow-y-auto rounded-lg border border-neutral-900 bg-black/60 p-2.5 font-mono text-[11px] space-y-1.5">
          {events.length === 0 ? (
            <p className="text-neutral-600 text-center py-8">
              Awaiting stream segment and chunk notifications...
            </p>
          ) : (
            events.map((ev, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between text-neutral-300 border-b border-neutral-900/60 pb-1"
              >
                <span className="text-emerald-400">[{ev.type}]</span>
                <span className="text-neutral-400">{ev.event || "-"}</span>
                <span className="text-neutral-600 text-[10px]">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ""}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
