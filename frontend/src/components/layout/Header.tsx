import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Plus, Activity, Cpu } from 'lucide-react';
import { useAnalysis } from '../../context/AnalysisContext';

interface HeaderProps {
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const location = useLocation();
  const { modelBackend, setModelBackend, currentAnalysis, isDemo } = useAnalysis();

  const getPageTitle = (pathname: string) => {
    switch (pathname) {
      case '/': return 'Executive Intelligence Dashboard';
      case '/analyze': return 'Resume Analyzer & Multi-tier Parser';
      case '/results': return 'Candidate Compatibility Assessment';
      case '/skill-gap': return 'Skill Gap & Evidence Analysis';
      case '/career-mentor': return 'Personalized Career Mentor';
      case '/interview-studio': return 'Interview Intelligence Studio';
      case '/interview-practice': return 'Interactive Practice Mode';
      case '/interview-results': return 'Interview Heuristic Evaluation';
      case '/model-performance': return 'Supervised ML Model Performance';
      case '/datasets': return 'Dataset Provenance & Class Distribution';
      default: return 'ResumeMatch AI';
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-20 w-full items-center justify-between border-b border-slate-800/80 bg-[#0B0F19]/90 px-6 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight sm:text-xl">
            {getPageTitle(location.pathname)}
          </h1>
          <p className="hidden text-xs text-slate-400 sm:block">
            Multimodal matching & evidence-backed skill gap analysis
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Model Selection Selector */}
        <div className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-1.5 md:flex">
          <Cpu className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-medium text-slate-400">Backend:</span>
          <select
            value={modelBackend}
            onChange={(e) => setModelBackend(e.target.value as any)}
            className="bg-transparent text-xs font-semibold text-slate-200 outline-none cursor-pointer"
          >
            <option value="production" className="bg-slate-900 text-slate-200">
              Logistic Regression (Baseline)
            </option>
            <option value="challenger_m5" className="bg-slate-900 text-slate-200">
              Model 5 (Semantic Fusion)
            </option>
          </select>
        </div>

        {/* Dossier status badge */}
        {isDemo ? (
          <div className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
            <span>DEMO PREVIEW</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-indigo-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
            <span className="truncate max-w-[120px] sm:max-w-[180px]">
              {currentAnalysis?.filename || 'Active Candidate'}
            </span>
          </div>
        )}

        {/* Live operational badge */}
        <div className="hidden items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 sm:flex">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="hidden xl:inline">Operational • 0 LLM</span>
          <Activity className="h-3.5 w-3.5 xl:hidden" />
        </div>

        {/* New Analysis CTA */}
        <Link
          to="/analyze"
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition hover:bg-indigo-500"
        >
          <Plus className="h-4 w-4" />
          <span>New Analysis</span>
        </Link>
      </div>
    </header>
  );
};
