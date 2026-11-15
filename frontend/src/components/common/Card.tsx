import React from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: React.ElementType;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  icon: Icon,
  badge,
  actions,
  children,
  className = '',
  headerClassName = '',
  bodyClassName = '',
}) => {
  return (
    <div
      className={`rounded-xl border border-slate-800/80 bg-[#0F172A]/70 shadow-xl shadow-black/20 backdrop-blur-sm transition-all duration-200 ${className}`}
    >
      {(title || Icon || actions) && (
        <div
          className={`flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 px-6 py-4 ${headerClassName}`}
        >
          <div className="flex items-center gap-3">
            {Icon && (
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Icon className="h-5 w-5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                {title && <h3 className="font-semibold text-slate-100">{title}</h3>}
                {badge}
              </div>
              {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={`p-6 ${bodyClassName}`}>{children}</div>
    </div>
  );
};
