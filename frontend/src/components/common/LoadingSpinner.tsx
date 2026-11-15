import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading intelligence engine...',
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center py-16 text-center ${className}`}>
      <div className="relative flex h-14 w-14 items-center justify-center">
        <div className="absolute inset-0 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
        <Loader2 className="h-6 w-6 text-indigo-400 animate-pulse" />
      </div>
      <p className="mt-4 text-sm font-medium text-slate-300">{message}</p>
      <p className="mt-1 text-xs text-slate-400">Zero LLM • 100% Deterministic Engine</p>
    </div>
  );
};
