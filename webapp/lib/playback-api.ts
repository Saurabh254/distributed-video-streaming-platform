export interface PlaybackSession {
  session_id: string;
  video_id: string;
  title: string;
  stream_type: "hls" | "mp4";
  playback_url: string;
  hls_master_playlist_url: string | null;
  qualities: string[];
  duration_seconds: number;
  thumbnail_url: string | null;
  views_count: number;
  resume_position_seconds: number;
  status: string;
  hls_status: string;
}

export interface HeartbeatResult {
  status: string;
  session_id: string;
  current_time: number;
  view_recorded: boolean;
  current_views: number;
}

export async function fetchPlaybackSession(videoId: string): Promise<PlaybackSession> {
  const res = await fetch(`/api/playback/${videoId}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to initiate playback (${res.status})`);
  }
  return res.json();
}

export async function sendPlaybackHeartbeat(
  videoId: string,
  sessionId: string,
  currentTime: number,
  duration?: number,
  isPaused: boolean = false
): Promise<HeartbeatResult> {
  const res = await fetch(`/api/playback/${videoId}/heartbeat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      current_time: currentTime,
      duration: duration || null,
      is_paused: isPaused,
    }),
  });

  if (!res.ok) {
    throw new Error(`Heartbeat failed (${res.status})`);
  }
  return res.json();
}

export async function fetchResumePosition(videoId: string): Promise<{
  video_id: string;
  resume_position_seconds: number;
  completed: boolean;
}> {
  const res = await fetch(`/api/playback/${videoId}/resume`);
  if (!res.ok) {
    return { video_id: videoId, resume_position_seconds: 0.0, completed: false };
  }
  return res.json();
}
