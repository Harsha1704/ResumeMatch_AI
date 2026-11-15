import React from 'react';

interface SingleProgressBarProps {
  percentage: number;
  color?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'blue';
  showLabel?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<SingleProgressBarProps> = ({
  percentage,
  color = 'indigo',
  showLabel = false,
  className = '',
}) => {
  const boundedPct = Math.min(100, Math.max(0, percentage));
  const colorMap = {
    indigo: 'bg-indigo-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    blue: 'bg-blue-500',
  };

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between text-xs font-medium text-slate-400 mb-1.5">
          <span>Progress</span>
          <span>{boundedPct.toFixed(1)}%</span>
        </div>
      )}
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full transition-all duration-500 rounded-full ${colorMap[color]}`}
          style={{ width: `${boundedPct}%` }}
        />
      </div>
    </div>
  );
};

interface MultiClassProgressBarProps {
  probabilities: {
    "Good Fit": number;
    "Potential Fit": number;
    "No Fit": number;
    [key: string]: number;
  };
}

export const MultiClassProgressBar: React.FC<MultiClassProgressBarProps> = ({ probabilities }) => {
  const goodFit = (probabilities["Good Fit"] || 0) * 100;
  const potentialFit = (probabilities["Potential Fit"] || 0) * 100;
  const noFit = (probabilities["No Fit"] || 0) * 100;

  return (
    <div className="w-full space-y-2">
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800 flex shadow-inner">
        <div
          style={{ width: `${goodFit}%` }}
          className="bg-emerald-500 transition-all duration-500 hover:opacity-90"
          title={`Good Fit: ${goodFit.toFixed(1)}%`}
        />
        <div
          style={{ width: `${potentialFit}%` }}
          className="bg-amber-500 transition-all duration-500 hover:opacity-90"
          title={`Potential Fit: ${potentialFit.toFixed(1)}%`}
        />
        <div
          style={{ width: `${noFit}%` }}
          className="bg-rose-500 transition-all duration-500 hover:opacity-90"
          title={`No Fit: ${noFit.toFixed(1)}%`}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <span className="text-slate-300 font-medium">Good Fit:</span>
          <span className="font-bold text-emerald-400">{goodFit.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
          <span className="text-slate-300 font-medium">Potential Fit:</span>
          <span className="font-bold text-amber-400">{potentialFit.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
          <span className="text-slate-300 font-medium">No Fit:</span>
          <span className="font-bold text-rose-400">{noFit.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
};
