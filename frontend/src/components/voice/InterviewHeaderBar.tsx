import React, { useState, useEffect } from 'react';
import { Timer, Sparkles, ShieldCheck, Square, Award, Cpu } from 'lucide-react';

interface InterviewHeaderBarProps {
  sessionId: string | null;
  targetRole: string;
  difficulty: string;
  currentIndex: number;
  totalQuestions: number;
  isCompleted: boolean;
  onOpenPrivacy: () => void;
  onEndInterview: () => void;
}

export const InterviewHeaderBar: React.FC<InterviewHeaderBarProps> = ({
  sessionId,
  targetRole,
  difficulty,
  currentIndex,
  totalQuestions,
  isCompleted,
  onOpenPrivacy,
  onEndInterview,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Timer: starts on sessionId, stops on isCompleted, cleans up on unmount
  useEffect(() => {
    if (!sessionId || isCompleted) return;

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionId, isCompleted]);

  const formatTime = (totalSecs: number) => {
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const progressPercent = totalQuestions > 0 ? Math.min(100, Math.round(((currentIndex + 1) / totalQuestions) * 100)) : 0;

  return (
    <header
      className="p-4 sm:p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur-md space-y-3"
      role="banner"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Title, Role & Difficulty */}
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              AI Voice Interview Room
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              ₹0 Budget
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span className="font-medium text-slate-200">{targetRole}</span>
            <span>•</span>
            <span className="capitalize text-slate-300">{difficulty} Difficulty</span>
            <span>•</span>
            <span className="inline-flex items-center gap-1 text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              Local AI Engine
            </span>
          </div>
        </div>

        {/* Status Indicators & Session Controls */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Real-time Elapsed Timer */}
          {sessionId && !isCompleted && (
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/90 border border-slate-700/80 text-xs font-mono font-medium text-slate-200 shadow-inner"
              title="Interview elapsed duration"
              aria-label={`Elapsed time: ${formatTime(elapsedSeconds)}`}
            >
              <Timer className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
              <span>{formatTime(elapsedSeconds)}</span>
            </div>
          )}

          {/* Privacy & Audio Policy trigger */}
          <button
            onClick={onOpenPrivacy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-white transition cursor-pointer"
            aria-label="Open privacy and audio disclosure policy"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Privacy</span>
          </button>

          {/* End Session Button if active */}
          {sessionId && !isCompleted && (
            <button
              onClick={onEndInterview}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 transition cursor-pointer"
              aria-label="End interview session early"
            >
              <Square className="w-3.5 h-3.5" />
              <span>End Session</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar & Question Counter when interview is active */}
      {sessionId && !isCompleted && totalQuestions > 0 && (
        <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-200">
              Question {currentIndex + 1} of {totalQuestions}
            </span>
            <span className="text-slate-400 font-mono text-[11px]">{progressPercent}% Completed</span>
          </div>

          <div
            className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={progressPercent}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}
    </header>
  );
};
