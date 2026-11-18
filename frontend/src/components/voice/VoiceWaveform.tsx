import React from 'react';

export type WaveformMode = 'idle' | 'listening' | 'speaking' | 'thinking';

interface VoiceWaveformProps {
  mode: WaveformMode;
  label?: string;
  barCount?: number;
}

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({
  mode,
  label,
  barCount = 20,
}) => {
  // Pre-calculated base heights for aesthetic rhythm
  const barHeights = [
    24, 45, 70, 95, 60, 85, 100, 75, 45, 90, 80, 55, 95, 70, 85, 60, 40, 75, 50, 30,
  ];

  const getModeStyles = () => {
    switch (mode) {
      case 'speaking':
        return {
          barColor: 'bg-gradient-to-t from-indigo-600 via-indigo-400 to-purple-400',
          shadow: 'shadow-indigo-500/30',
          label: label || 'AI Interviewer Speech Output',
          statusColor: 'text-indigo-400',
        };
      case 'listening':
        return {
          barColor: 'bg-gradient-to-t from-emerald-600 via-teal-400 to-cyan-400',
          shadow: 'shadow-emerald-500/30',
          label: label || 'Candidate Voice Recognition Active',
          statusColor: 'text-emerald-400',
        };
      case 'thinking':
        return {
          barColor: 'bg-gradient-to-t from-amber-600 via-amber-400 to-yellow-300',
          shadow: 'shadow-amber-500/30',
          label: label || 'Evaluating Candidate Response',
          statusColor: 'text-amber-400',
        };
      case 'idle':
      default:
        return {
          barColor: 'bg-slate-700/60',
          shadow: 'shadow-none',
          label: label || 'Voice Channel Ready',
          statusColor: 'text-slate-500',
        };
    }
  };

  const { barColor, shadow, label: activeLabel, statusColor } = getModeStyles();

  return (
    <div
      className="flex flex-col items-center justify-center p-3 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm space-y-2 select-none w-full max-w-md mx-auto"
      role="img"
      aria-label={`Voice activity waveform: currently ${activeLabel}`}
    >
      {/* Waveform Bar Equalizer Container */}
      <div className="flex items-center justify-center gap-1.5 h-12 w-full px-4 overflow-hidden">
        {Array.from({ length: barCount }).map((_, idx) => {
          const heightPercent = barHeights[idx % barHeights.length];
          const isAnimated = mode !== 'idle';

          // Staggered animation delay for natural organic wave motion
          const delay = `${(idx * 0.08).toFixed(2)}s`;
          const duration = mode === 'speaking' ? '1.1s' : mode === 'listening' ? '1.4s' : '1.8s';

          const computedHeight =
            mode === 'idle'
              ? '12%'
              : `${Math.max(20, heightPercent * (mode === 'thinking' ? 0.6 : 1))}%`;

          return (
            <div
              key={idx}
              className={`w-1 sm:w-1.5 rounded-full transition-all duration-300 ${barColor} ${shadow}`}
              style={{
                height: computedHeight,
                animationName: isAnimated ? 'voiceWavePulse' : 'none',
                animationDuration: duration,
                animationIterationCount: 'infinite',
                animationTimingFunction: 'ease-in-out',
                animationDelay: delay,
              }}
            />
          );
        })}
      </div>

      {/* State-driven description (no fake decibel or emotion claims) */}
      <div className="flex items-center justify-between w-full px-2 text-[11px] text-slate-400 border-t border-slate-800/60 pt-1.5">
        <span className="flex items-center gap-1.5 font-medium">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              mode === 'speaking'
                ? 'bg-indigo-400'
                : mode === 'listening'
                ? 'bg-emerald-400'
                : mode === 'thinking'
                ? 'bg-amber-400'
                : 'bg-slate-600'
            }`}
          />
          <span className={statusColor}>{activeLabel}</span>
        </span>
        <span className="text-[10px] text-slate-500 font-mono">
          {mode === 'idle' ? 'STANDBY' : mode.toUpperCase()}
        </span>
      </div>

      {/* Embedded CSS animation for responsive wave pulses with reduced-motion safety */}
      <style>{`
        @keyframes voiceWavePulse {
          0%, 100% {
            transform: scaleY(0.35);
          }
          50% {
            transform: scaleY(1.0);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .voiceWavePulse, div[style*="voiceWavePulse"] {
            animation: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};
