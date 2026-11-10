"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type LiveConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting";

export interface LiveStreamEvent {
  type: string;
  stream_id?: string;
  sender?: string;
  event?: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
}

interface UseLiveStreamOptions {
  streamId: string;
  autoConnect?: boolean;
  heartbeatIntervalMs?: number;
  heartbeatTimeoutMs?: number;
  wsUrl?: string;
}

export function useLiveStream({
  streamId,
  autoConnect = true,
  heartbeatIntervalMs = 10000,
  heartbeatTimeoutMs = 25000,
  wsUrl,
}: UseLiveStreamOptions) {
  const [status, setStatus] = useState<LiveConnectionStatus>("disconnected");
  const [viewerCount, setViewerCount] = useState<number>(0);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [events, setEvents] = useState<LiveStreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const timeoutCheckTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastPongTimeRef = useRef<number>(0);
  const reconnectAttemptRef = useRef<number>(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const connectRef = useRef<(() => void) | null>(null);

  const clearTimers = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (timeoutCheckTimerRef.current) {
      clearInterval(timeoutCheckTimerRef.current);
      timeoutCheckTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    clearTimers();
    setStatus("connecting");
    setError(null);

    const baseUrl =
      wsUrl ||
      process.env.NEXT_PUBLIC_VIDEO_WS_URL ||
      "ws://127.0.0.1:8001";
    const fullUrl = `${baseUrl}/api/v1/live/ws/${streamId}`;

    try {
      const ws = new WebSocket(fullUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        const now = Date.now();
        setStatus("connected");
        reconnectAttemptRef.current = 0;
        lastPongTimeRef.current = now;
        setLastHeartbeat(new Date(now));

        // Start heartbeat ping loop
        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const sendTimestamp = Date.now();
            ws.send(JSON.stringify({ type: "ping", timestamp: sendTimestamp }));
          }
        }, heartbeatIntervalMs);

        // Start heartbeat timeout inspector (detects silent disconnects)
        timeoutCheckTimerRef.current = setInterval(() => {
          const currentTime = Date.now();
          if (currentTime - lastPongTimeRef.current > heartbeatTimeoutMs) {
            console.warn(
              `LiveStream WebSocket heartbeat timeout exceeded (> ${heartbeatTimeoutMs}ms). Disconnecting.`
            );
            setStatus("disconnected");
            setError("Heartbeat timeout - connection lost");
            ws.close();
          }
        }, 3000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "pong") {
            const now = Date.now();
            lastPongTimeRef.current = now;
            setLastHeartbeat(new Date(now));
            if (msg.client_timestamp) {
              setLatencyMs(now - msg.client_timestamp);
            }
          } else if (msg.type === "connection_established") {
            if (typeof msg.viewer_count === "number") {
              setViewerCount(msg.viewer_count);
            }
          } else if (msg.type === "status_response") {
            if (typeof msg.viewer_count === "number") {
              setViewerCount(msg.viewer_count);
            }
          } else if (msg.type === "stream_update") {
            setEvents((prev) => [msg, ...prev.slice(0, 49)]);
          }
        } catch {
          // ignore non-json messages
        }
      };

      ws.onclose = (event) => {
        clearTimers();
        setStatus("disconnected");
        socketRef.current = null;

        // Auto reconnect with exponential backoff if not closed cleanly
        if (event.code !== 1000) {
          const attempt = reconnectAttemptRef.current + 1;
          reconnectAttemptRef.current = attempt;
          const delay = Math.min(1000 * Math.pow(1.5, attempt), 10000);
          setStatus("reconnecting");
          reconnectTimerRef.current = setTimeout(() => {
            if (connectRef.current) {
              connectRef.current();
            }
          }, delay);
        }
      };

      ws.onerror = () => {
        setError("WebSocket communication error occurred");
      };
    } catch (err: unknown) {
      setStatus("disconnected");
      setError(err instanceof Error ? err.message : "Failed to open WebSocket");
    }
  }, [streamId, wsUrl, heartbeatIntervalMs, heartbeatTimeoutMs, clearTimers]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    clearTimers();
    if (socketRef.current) {
      socketRef.current.close(1000, "Client initiated disconnect");
      socketRef.current = null;
    }
    setStatus("disconnected");
  }, [clearTimers]);

  const broadcast = useCallback(
    (event: string, payload: Record<string, unknown>) => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            type: "broadcast",
            event,
            payload,
          })
        );
      }
    },
    []
  );

  useEffect(() => {
    if (autoConnect && streamId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, streamId, connect, disconnect]);

  return {
    status,
    viewerCount,
    latencyMs,
    lastHeartbeat,
    events,
    error,
    connect,
    disconnect,
    broadcast,
  };
}
