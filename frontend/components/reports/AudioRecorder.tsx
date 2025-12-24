'use client';

import { useState, useEffect } from 'react';
import { Mic, Square, Pause, Play, Trash2 } from 'lucide-react';

interface AudioRecorderProps {
  audioBlob: Blob | null;
  onAudioChange: (blob: Blob | null) => void;
  disabled?: boolean;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function isAudioRecordingSupported(): boolean {
  if (typeof window === 'undefined') return false;
  if (typeof navigator === 'undefined') return false;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
  if (typeof MediaRecorder === 'undefined') return false;
  return true;
}

export function AudioRecorder({ audioBlob, onAudioChange, disabled = false }: AudioRecorderProps) {
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [chunks, setChunks] = useState<Blob[]>([]);

  useEffect(() => {
    setIsSupported(isAudioRecordingSupported());
  }, []);

  // Cleanup audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  // Timer for duration
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isRecording && !isPaused) {
      interval = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording, isPaused]);

  const handleStartRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

      const recorder = new MediaRecorder(stream, { mimeType });
      const recordedChunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
          setChunks([...recordedChunks]);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: mimeType });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        onAudioChange(blob);
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start(100);
      setMediaRecorder(recorder);
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('Permissao de microfone negada');
        } else if (err.name === 'NotFoundError') {
          setError('Microfone nao encontrado');
        } else {
          setError('Erro ao acessar microfone');
        }
      }
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const handlePauseRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause();
      setIsPaused(true);
    }
  };

  const handleResumeRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume();
      setIsPaused(false);
    }
  };

  const handleClear = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setDuration(0);
    setChunks([]);
    onAudioChange(null);
  };

  // Don't render anything until we know if it's supported
  if (isSupported === null) return null;

  // Don't render if not supported
  if (!isSupported) return null;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-zinc-700">
        Audio (opcional)
      </label>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {!isRecording && !audioUrl && (
        <button
          type="button"
          onClick={handleStartRecording}
          disabled={disabled}
          className="w-full h-16 border-2 border-dashed border-zinc-300 rounded-lg
                     flex items-center justify-center gap-2
                     text-zinc-500 hover:border-red-300 hover:text-red-500
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Mic className="w-5 h-5" />
          <span className="text-sm">Clique para gravar audio</span>
        </button>
      )}

      {isRecording && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span className="text-red-700 font-medium">
                {isPaused ? 'Pausado' : 'Gravando'}
              </span>
              <span className="text-red-600">{formatDuration(duration)}</span>
            </div>
            <div className="flex items-center gap-2">
              {isPaused ? (
                <button
                  type="button"
                  onClick={handleResumeRecording}
                  className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600"
                >
                  <Play className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handlePauseRecording}
                  className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600"
                >
                  <Pause className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={handleStopRecording}
                className="p-2 bg-zinc-700 text-white rounded-full hover:bg-zinc-800"
              >
                <Square className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {audioUrl && !isRecording && (
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-3">
          <div className="flex items-center gap-3">
            <audio src={audioUrl} controls className="flex-1 h-10" />
            <button
              type="button"
              onClick={handleClear}
              disabled={disabled}
              className="p-2 text-red-500 hover:bg-red-50 rounded-full
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
