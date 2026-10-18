"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize } from "lucide-react";
import Hls from "hls.js";
import { Video } from "@/lib/types";
import { sendPlaybackHeartbeat } from "@/lib/playback-api";

interface VideoPlayerProps {
  video: Video;
  streamUrl?: string;
  sessionId?: string;
  resumePosition?: number;
  onEnded?: () => void;
  onViewCountUpdate?: (newViews: number) => void;
}

export function VideoPlayer({
  video,
  streamUrl,
  sessionId,
  resumePosition = 0,
  onEnded,
  onViewCountUpdate,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(video.durationSeconds || 100);
  const [volume] = useState(0.85);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const initialSeekDoneRef = useRef(false);

  const activeUrl = streamUrl || video.videoUrl;

  // Initialize HLS or Native playback
  useEffect(() => {
    const videoEl = videoRef.current;
    if (!videoEl || !activeUrl) return;

    initialSeekDoneRef.current = false;

    // Destroy existing HLS instance if any
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    const isHlsStream = activeUrl.includes(".m3u8") || activeUrl.includes("/hls/");

    if (isHlsStream && Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      hlsRef.current = hls;

      hls.loadSource(activeUrl);
      hls.attachMedia(videoEl);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (resumePosition > 0 && !initialSeekDoneRef.current) {
          videoEl.currentTime = resumePosition;
          initialSeekDoneRef.current = true;
        }
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
              break;
          }
        }
      });
    } else if (videoEl.canPlayType("application/vnd.apple.mpegurl") || !isHlsStream) {
      // Native Safari HLS or regular MP4 stream
      videoEl.src = activeUrl;
      videoEl.load();
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [activeUrl, resumePosition]);

  // Periodic Telemetry Heartbeat
  useEffect(() => {
    if (!sessionId || !isPlaying) return;

    const interval = setInterval(async () => {
      const current = videoRef.current?.currentTime || 0;
      const total = videoRef.current?.duration || duration;
      try {
        const res = await sendPlaybackHeartbeat(video.id, sessionId, current, total, false);
        if (res.view_recorded && onViewCountUpdate) {
          onViewCountUpdate(res.current_views);
        }
      } catch (err) {
        console.debug("Heartbeat ping failed:", err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [sessionId, isPlaying, video.id, duration, onViewCountUpdate]);

  const handleMouseMove = () => {
    setShowControls(true);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      if (isPlaying) setShowControls(false);
    }, 2500);
  };

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const toggleMute = useCallback(() => {
    if (!videoRef.current) return;
    if (isMuted) {
      videoRef.current.volume = volume || 0.5;
      setIsMuted(false);
    } else {
      videoRef.current.volume = 0;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  }, []);

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) videoRef.current.currentTime = time;
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName || "")) return;
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "KeyM") {
        toggleMute();
      } else if (e.code === "KeyF") {
        toggleFullscreen();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePlay, toggleMute, toggleFullscreen]);

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => isPlaying && setShowControls(false)}
      className="group relative aspect-video w-full overflow-hidden rounded-lg bg-black select-none border border-neutral-900"
    >
      <video
        ref={videoRef}
        poster={video.thumbnail}
        onTimeUpdate={() => videoRef.current && setCurrentTime(videoRef.current.currentTime)}
        onLoadedMetadata={() => {
          if (videoRef.current) {
            setDuration(videoRef.current.duration || video.durationSeconds || 100);
            if (resumePosition > 0 && !initialSeekDoneRef.current) {
              videoRef.current.currentTime = resumePosition;
              initialSeekDoneRef.current = true;
            }
          }
        }}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          setIsPlaying(false);
          onEnded?.();
        }}
        onClick={togglePlay}
        className="h-full w-full object-contain cursor-pointer"
        playsInline
      />

      {/* Pure Minimal Controls Overlay */}
      <div
        className={`absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/80 to-transparent transition-opacity duration-200 ${
          showControls ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Progress Bar */}
        <div className="relative flex items-center mb-2.5">
          <div className="h-0.5 w-full bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-neutral-200 transition-all duration-75"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <input
            type="range"
            min={0}
            max={duration || 100}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
        </div>

        {/* Buttons Bar */}
        <div className="flex items-center justify-between text-neutral-300 text-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={togglePlay}
              className="hover:text-white transition-colors"
              title={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </button>

            <button
              onClick={toggleMute}
              className="hover:text-white transition-colors"
              title={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </button>

            <span className="font-mono text-[11px] text-neutral-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleFullscreen}
              className="hover:text-white transition-colors"
              title="Fullscreen"
            >
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
