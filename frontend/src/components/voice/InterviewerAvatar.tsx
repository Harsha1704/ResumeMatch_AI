import React from 'react';
import { Bot, Radio, Cpu, Volume2, Mic } from 'lucide-react';

export type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface InterviewerAvatarProps {
  state: AvatarState;
  interviewerName?: string;
  isMuted?: boolean;
}

export const InterviewerAvatar: React.FC<InterviewerAvatarProps> = ({
  state,
  interviewerName = 'ResumeMatch AI',
  isMuted = false,
}) => {
  // Color accents based on active state
  const getTheme = () => {
    switch (state) {
      case 'speaking':
        return {
          ring: 'border-indigo-500/60 shadow-indigo-500/30',
          core: 'from-indigo-600 via-indigo-500 to-purple-600 text-white',
          glow: 'bg-indigo-500/20',
          pulse: 'animate-pulse',
          badgeBg: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300',
          badgeText: 'Speaking',
          icon: Volume2,
        };
      case 'listening':
        return {
          ring: 'border-emerald-500/60 shadow-emerald-500/30',
          core: 'from-emerald-600 via-teal-500 to-cyan-600 text-white',
          glow: 'bg-emerald-500/20',
          pulse: 'animate-pulse',
          badgeBg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
          badgeText: 'Listening to You',
          icon: Mic,
        };
      case 'thinking':
        return {
          ring: 'border-amber-500/60 shadow-amber-500/30',
          core: 'from-amber-600 via-amber-500 to-orange-600 text-white',
          glow: 'bg-amber-500/20',
          pulse: 'animate-spin',
          badgeBg: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
          badgeText: 'Evaluating Answer',
          icon: Cpu,
        };
      case 'idle':
      default:
        return {
          ring: 'border-slate-700 shadow-slate-900/50',
          core: 'from-slate-800 via-slate-700 to-slate-800 text-slate-300',
          glow: 'bg-slate-800/20',
          pulse: '',
          badgeBg: 'bg-slate-800/80 border-slate-700 text-slate-400',
          badgeText: 'Standby',
          icon: Bot,
        };
    }
  };

  const theme = getTheme();
  const IconComponent = theme.icon;

  return (
    <div
      className="flex flex-col items-center justify-center space-y-4 select-none"
      role="region"
      aria-label={`AI Interviewer Avatar: currently ${theme.badgeText}`}
    >
      {/* Outer ambient glow and multi-tier concentric rings */}
      <div className="relative flex items-center justify-center w-36 h-36 sm:w-44 sm:h-44">
        {/* Ambient atmospheric backdrop */}
        <div
          className={`absolute inset-0 rounded-full blur-2xl transition-all duration-700 ${theme.glow}`}
          aria-hidden="true"
        />

        {/* Outermost resonant ring for speaking/listening */}
        {(state === 'speaking' || state === 'listening') && (
          <div
            className={`absolute inset-0 rounded-full border border-dashed ${theme.ring} animate-ping opacity-25`}
            style={{ animationDuration: state === 'speaking' ? '2.5s' : '3s' }}
            aria-hidden="true"
          />
        )}

        {/* Secondary rotating geometric orbital ring */}
        <div
          className={`absolute inset-2 sm:inset-3 rounded-full border border-slate-800/80 ${
            state === 'thinking' ? 'border-t-amber-400 border-r-amber-500 animate-spin' : ''
          }`}
          style={{ animationDuration: '4s' }}
          aria-hidden="true"
        />

        {/* Primary avatar border ring with shadow glow */}
        <div
          className={`absolute inset-5 sm:inset-6 rounded-full border-2 transition-all duration-500 shadow-lg ${theme.ring} bg-slate-950/80 backdrop-blur-md flex items-center justify-center`}
        >
          {/* Inner core orb */}
          <div
            className={`w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-tr ${theme.core} shadow-inner flex items-center justify-center transition-all duration-500`}
          >
            <IconComponent
              className={`w-8 h-8 sm:w-10 sm:h-10 transition-transform duration-300 ${
                state === 'speaking' ? 'scale-110' : state === 'listening' ? 'scale-105' : 'scale-100'
              }`}
            />
          </div>
        </div>

        {/* Muted indicator badge if output is silenced */}
        {isMuted && (
          <span
            className="absolute top-1 right-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 border border-amber-500/40 text-amber-300 shadow-md"
            title="Interviewer speech audio muted"
          >
            Muted
          </span>
        )}
      </div>

      {/* Identity & Status Pill */}
      <div className="flex flex-col items-center space-y-1.5 text-center">
        <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
          <span>{interviewerName}</span>
          <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
            AI Host
          </span>
        </h3>

        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-300 ${theme.badgeBg}`}
        >
          <span className="relative flex h-2 w-2">
            {state !== 'idle' && (
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  state === 'speaking' ? 'bg-indigo-400' : state === 'listening' ? 'bg-emerald-400' : 'bg-amber-400'
                }`}
              />
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                state === 'speaking'
                  ? 'bg-indigo-400'
                  : state === 'listening'
                  ? 'bg-emerald-400'
                  : state === 'thinking'
                  ? 'bg-amber-400'
                  : 'bg-slate-500'
              }`}
            />
          </span>
          <span>{theme.badgeText}</span>
        </div>
      </div>
    </div>
  );
};
