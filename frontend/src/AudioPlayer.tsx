import { Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, CSSProperties, FocusEvent } from "react";

const HAVE_FUTURE_DATA = 3;
const NETWORK_IDLE = 1;
const STALL_RECOVERY_DELAY_MS = 180;
const STALL_NUDGE_SECONDS = 0.05;

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "0:00";
  const total = Math.floor(seconds);
  const minutes = Math.floor(total / 60);
  const remaining = String(total % 60).padStart(2, "0");
  return `${minutes}:${remaining}`;
}

function finiteDuration(value: number): number {
  return Number.isFinite(value) && value > 0 ? value : 0;
}

export function AudioPlayer({
  className,
  label,
  src,
}: {
  className?: string;
  label: string;
  src: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const shouldKeepPlayingRef = useRef(false);
  const recoveryTimerRef = useRef<number | undefined>(undefined);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isVolumeOpen, setIsVolumeOpen] = useState(false);
  const [volume, setVolume] = useState(1);
  const progress = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const isMuted = volume === 0;

  useEffect(() => {
    if (recoveryTimerRef.current !== undefined) {
      window.clearTimeout(recoveryTimerRef.current);
      recoveryTimerRef.current = undefined;
    }
    shouldKeepPlayingRef.current = false;
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = volume;
    audio.muted = isMuted;
  }, [isMuted, volume]);

  useEffect(() => {
    return () => {
      if (recoveryTimerRef.current !== undefined) {
        window.clearTimeout(recoveryTimerRef.current);
      }
    };
  }, []);

  const syncDuration = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setDuration(finiteDuration(audio.duration));
  };

  const syncCurrentTime = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setCurrentTime(audio.currentTime);
  };

  const primeForContinuousPlayback = (audio: HTMLAudioElement) => {
    audio.preload = "auto";
  };

  const nudgeIfBufferStalled = (audio: HTMLAudioElement) => {
    if (audio.readyState >= HAVE_FUTURE_DATA || audio.networkState !== NETWORK_IDLE) return;
    if (duration > 0 && audio.currentTime >= duration - STALL_NUDGE_SECONDS) return;

    const bufferedRanges = audio.buffered;
    let bufferedLead = 0;
    for (let i = 0; i < bufferedRanges.length; i += 1) {
      if (audio.currentTime >= bufferedRanges.start(i) && audio.currentTime <= bufferedRanges.end(i)) {
        bufferedLead = bufferedRanges.end(i) - audio.currentTime;
        break;
      }
    }
    if (bufferedLead > 0.25) return;

    const upperBound = duration > 0 ? Math.max(0, duration - STALL_NUDGE_SECONDS) : audio.currentTime + STALL_NUDGE_SECONDS;
    const nextTime = Math.min(audio.currentTime + STALL_NUDGE_SECONDS, upperBound);
    if (nextTime > audio.currentTime) audio.currentTime = nextTime;
  };

  const recoverPlayback = (delayMs = STALL_RECOVERY_DELAY_MS) => {
    const audio = audioRef.current;
    if (!audio || !shouldKeepPlayingRef.current || audio.ended) return;
    if (duration > 0 && audio.currentTime >= duration - 0.3) return;

    setIsPlaying(true);
    primeForContinuousPlayback(audio);
    if (recoveryTimerRef.current !== undefined) {
      window.clearTimeout(recoveryTimerRef.current);
    }
    recoveryTimerRef.current = window.setTimeout(() => {
      recoveryTimerRef.current = undefined;
      const latestAudio = audioRef.current;
      if (!latestAudio || !shouldKeepPlayingRef.current || latestAudio.ended) return;
      primeForContinuousPlayback(latestAudio);
      nudgeIfBufferStalled(latestAudio);
      void latestAudio.play().then(
        () => setIsPlaying(true),
        () => {
          shouldKeepPlayingRef.current = false;
          setIsPlaying(false);
        },
      );
    }, delayMs);
  };

  const togglePlayback = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      if (duration > 0 && audio.currentTime >= duration - 0.03) {
        audio.currentTime = 0;
        setCurrentTime(0);
      }
      shouldKeepPlayingRef.current = true;
      primeForContinuousPlayback(audio);
      try {
        await audio.play();
      } catch {
        shouldKeepPlayingRef.current = false;
        setIsPlaying(false);
      }
      return;
    }
    shouldKeepPlayingRef.current = false;
    if (recoveryTimerRef.current !== undefined) {
      window.clearTimeout(recoveryTimerRef.current);
      recoveryTimerRef.current = undefined;
    }
    audio.pause();
  };

  const handleNativePause = () => {
    const audio = audioRef.current;
    if (!audio || !shouldKeepPlayingRef.current || audio.ended) {
      setIsPlaying(false);
      return;
    }
    recoverPlayback();
  };

  const seek = (event: ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    const nextTime = duration > 0 ? Math.min(duration, Number(event.currentTarget.value)) : 0;
    setCurrentTime(nextTime);
    if (audio) {
      const shouldResume = shouldKeepPlayingRef.current;
      primeForContinuousPlayback(audio);
      audio.currentTime = nextTime;
      if (shouldResume) recoverPlayback(0);
    }
  };

  const changeVolume = (event: ChangeEvent<HTMLInputElement>) => {
    const nextVolume = Number(event.currentTarget.value);
    setVolume(Math.max(0, Math.min(1, nextVolume)));
  };

  const closeVolumeWhenFocusLeaves = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsVolumeOpen(false);
    }
  };

  return (
    <div
      className={["audio-player", className].filter(Boolean).join(" ")}
      style={
        {
          "--audio-progress": `${progress}%`,
          "--audio-volume": `${volume * 100}%`,
        } as CSSProperties
      }
    >
      <button
        aria-label={isPlaying ? `暂停 ${label}` : `播放 ${label}`}
        className="audio-player-button"
        onClick={togglePlayback}
        type="button"
      >
        {isPlaying ? <Pause size={15} fill="currentColor" /> : <Play size={15} fill="currentColor" />}
      </button>
      <span className="audio-player-time">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
      <input
        aria-label={`播放进度：${label}`}
        className="audio-player-scrubber"
        disabled={duration === 0}
        max={duration || 0}
        min="0"
        onChange={seek}
        step="0.1"
        type="range"
        value={duration > 0 ? Math.min(currentTime, duration) : 0}
      />
      <div className="audio-player-volume" onBlur={closeVolumeWhenFocusLeaves}>
        <button
          aria-expanded={isVolumeOpen}
          aria-label={`调整音量：${label}`}
          className="audio-player-button audio-player-volume-button"
          onClick={() => setIsVolumeOpen((open) => !open)}
          type="button"
        >
          {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
        </button>
        {isVolumeOpen ? (
          <div className="audio-player-volume-popover">
            <input
              aria-label={`音量：${label}`}
              className="audio-player-volume-slider"
              max="1"
              min="0"
              onChange={changeVolume}
              step="0.05"
              type="range"
              value={volume}
            />
          </div>
        ) : null}
      </div>
      <audio
        ref={audioRef}
        onDurationChange={syncDuration}
        onEnded={() => {
          shouldKeepPlayingRef.current = false;
          if (recoveryTimerRef.current !== undefined) {
            window.clearTimeout(recoveryTimerRef.current);
            recoveryTimerRef.current = undefined;
          }
          setIsPlaying(false);
          if (duration > 0) setCurrentTime(duration);
        }}
        onCanPlay={() => {
          const audio = audioRef.current;
          if (audio?.paused && shouldKeepPlayingRef.current) recoverPlayback(0);
        }}
        onLoadedMetadata={syncDuration}
        onPause={handleNativePause}
        onPlay={() => {
          shouldKeepPlayingRef.current = true;
          setIsPlaying(true);
        }}
        onPlaying={() => {
          if (recoveryTimerRef.current !== undefined) {
            window.clearTimeout(recoveryTimerRef.current);
            recoveryTimerRef.current = undefined;
          }
          setIsPlaying(true);
        }}
        onStalled={() => recoverPlayback()}
        onTimeUpdate={syncCurrentTime}
        onWaiting={() => recoverPlayback()}
        preload="metadata"
        src={src}
      />
    </div>
  );
}
