import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileSearch,
  CheckCircle2,
  GitCompare,
  GraduationCap,
  Sparkles,
  PlayCircle,
  Award,
  BarChart3,
  Database,
  Cpu,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';
import { useAnalysis } from '../../context/AnalysisContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { currentAnalysis, isDemo } = useAnalysis();

  const navGroups = [
    {
      title: 'CORE APPLICATION',
      items: [
        { name: 'Dashboard', path: '/', icon: LayoutDashboard },
        { name: 'Resume Analyzer', path: '/analyze', icon: FileSearch },
        { name: 'Analysis Results', path: '/results', icon: CheckCircle2 },
        { name: 'Skill Gap Analytics', path: '/skill-gap', icon: GitCompare },
      ],
    },
    {
      title: 'CAREER GUIDANCE',
      items: [
        { name: 'Career Mentor', path: '/career-mentor', icon: GraduationCap },
        { name: 'Interview Studio', path: '/interview-studio', icon: Sparkles },
        { name: 'Practice Mode', path: '/interview-practice', icon: PlayCircle },
        { name: 'Practice Results', path: '/interview-results', icon: Award },
      ],
    },
    {
      title: 'EVALUATION & DATA',
      items: [
        { name: 'Model Performance', path: '/model-performance', icon: BarChart3 },
        { name: 'Dataset Explorer', path: '/datasets', icon: Database },
      ],
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800 bg-[#0B0F19] transition-transform duration-300 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-20 items-center justify-between border-b border-slate-800/80 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/25">
              <Cpu className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-lg font-bold tracking-tight text-white">ResumeMatch</span>
                <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-400 border border-indigo-500/30">AI</span>
              </div>
              <p className="text-[11px] font-medium text-slate-400">Deterministic Matcher</p>
            </div>
          </div>
        </div>

        {/* Deterministic System Banner */}
        <div className="mx-4 mt-4 rounded-lg border border-emerald-500/20 bg-emerald-950/20 px-3 py-2 text-xs">
          <div className="flex items-center gap-2 font-medium text-emerald-400">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-400" />
            <span>Zero LLM • 100% Deterministic</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Scikit-Learn ML + Strict Evidence</p>
        </div>

        {/* Navigation Groups */}
        <nav className="flex-1 space-y-6 overflow-y-auto px-4 py-4 text-sm scrollbar-thin scrollbar-thumb-slate-800">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              <h3 className="px-3 text-[11px] font-semibold tracking-wider text-slate-500">
                {group.title}
              </h3>
              <div className="space-y-0.5 pt-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `group flex items-center justify-between rounded-lg px-3 py-2.5 font-medium transition-all duration-150 ${
                          isActive
                            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25'
                            : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                        }`
                      }
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110" />
                        <span>{item.name}</span>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Active Analysis Candidate Drawer Footer */}
        {currentAnalysis && (
          <div className="border-t border-slate-800/80 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded ${
                isDemo
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
              }`}>
                {isDemo ? 'DEMO PREVIEW' : 'ACTIVE DOSSIER'}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                  currentAnalysis.predicted_class === 'Good Fit'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : currentAnalysis.predicted_class === 'Potential Fit'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                }`}
              >
                {currentAnalysis.compatibility_score}% Score
              </span>
            </div>
            <div className="mt-2 truncate text-sm font-semibold text-slate-200">
              {currentAnalysis.job_title || 'Software Engineer'}
            </div>
            <div className="truncate text-xs text-slate-400">
              {currentAnalysis.filename || 'Candidate Resume'}
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
