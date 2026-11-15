import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  badge?: React.ReactNode;
  accent?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'blue' | 'purple';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  accent = 'indigo',
  className = '',
}) => {
  const accentBorder = {
    indigo: 'from-indigo-500/20 via-indigo-500/5 to-transparent',
    emerald: 'from-emerald-500/20 via-emerald-500/5 to-transparent',
    amber: 'from-amber-500/20 via-amber-500/5 to-transparent',
    rose: 'from-rose-500/20 via-rose-500/5 to-transparent',
    blue: 'from-blue-500/20 via-blue-500/5 to-transparent',
    purple: 'from-purple-500/20 via-purple-500/5 to-transparent',
  };

  const iconColors = {
    indigo: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  };

  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]/80 p-5 shadow-lg backdrop-blur-sm transition-all duration-200 hover:border-slate-700 hover:shadow-xl ${className}`}
    >
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${accentBorder[accent]}`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold tracking-wide uppercase text-slate-400">
            {title}
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black tracking-tight text-white sm:text-3xl">
              {value}
            </span>
            {badge}
          </div>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
          )}
        </div>
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl border ${iconColors[accent]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
};
