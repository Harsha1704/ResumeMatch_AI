import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  GitCompare,
  FileSearch,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ExternalLink,
  BookOpen,
  PieChart as PieIcon,
  BarChart3,
  Award,
  ArrowRight,
  ListOrdered,
  Sparkles
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { AnalysisResult } from '../types';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

export const SkillGapPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlId = searchParams.get('id');
  const { currentAnalysis, loadAnalysis, isLoading } = useAnalysis();

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(currentAnalysis);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (urlId && urlId !== analysis?.analysis_id) {
      setFetching(true);
      api.getSkillGap(urlId)
        .then((res) => {
          if (res.analysis) setAnalysis(res.analysis);
        })
        .catch(() => {
          loadAnalysis(urlId).then((res) => {
            if (res) setAnalysis(res);
          });
        })
        .finally(() => setFetching(false));
    } else if (!analysis && currentAnalysis) {
      setAnalysis(currentAnalysis);
    }
  }, [urlId, currentAnalysis, analysis, loadAnalysis]);

  if (isLoading || fetching) {
    return <LoadingSpinner message="Calculating deterministic skill coverage..." />;
  }

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-800 bg-[#0F172A]/60 p-12 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-4">
          <GitCompare className="h-8 w-8" />
        </div>
        <h3 className="text-xl font-bold text-white">No Active Resume Analysis Found</h3>
        <p className="mt-2 max-w-md text-xs text-slate-400 leading-relaxed">
          Upload a student resume and target job description in the Analyzer to populate real-time skill gap graphs, coverage metrics, and learning roadmaps.
        </p>
        <Link
          to="/analyze"
          className="mt-6 flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500"
        >
          <FileSearch className="h-4 w-4" />
          <span>Go to Resume Analyzer</span>
        </Link>
      </div>
    );
  }

  const gapSummary = analysis.skill_gap_summary || ({} as any);
  const fullCovPct = gapSummary.full_coverage_pct ?? 75.0;
  const remainingPct = Math.max(0, 100 - fullCovPct);

  const gaugeData = [
    { name: 'Covered', value: fullCovPct, color: '#10B981' },
    { name: 'Unmet', value: remainingPct, color: '#1E293B' },
  ];

  const barData = [
    {
      category: 'Matched Required',
      count: gapSummary.matched_required_count || (analysis.matched_required_skills?.length || 0),
      fill: '#10B981',
    },
    {
      category: 'Missing Required',
      count: gapSummary.missing_required_count || (analysis.missing_required_skills?.length || 0),
      fill: '#EF4444',
    },
    {
      category: 'Missing Preferred',
      count: gapSummary.missing_preferred_count || (analysis.missing_preferred_skills?.length || 0),
      fill: '#F59E0B',
    },
  ];

  const prioritizedGaps = (analysis as any).prioritized_gaps || (analysis.missing_required_skills || []).map((s) => ({
    skill: s,
    priority: 'High Priority',
    type: 'Mandatory Core',
    frequency_in_job: 2,
  }));

  const partialSkills = analysis.partially_evidenced_required_skills || (analysis as any).partially_evidenced_skills || [];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Interactive Skill Gap Analytics
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Deterministic breakdown of competencies, missing qualifications, and prioritized learning paths.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/results?id=${encodeURIComponent(analysis.analysis_id)}`}
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
          >
            View Full Results
          </Link>
          <Link
            to="/analyze"
            className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
          >
            New Analysis
          </Link>
        </div>
      </div>

      {analysis.is_demo && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Demo Preview Skill Gap Analysis</p>
              <p className="text-xs text-amber-400/80">You are viewing a demonstration profile. Submit your own resume in the Analyzer to evaluate actual compatibility.</p>
            </div>
          </div>
          <Link
            to="/analyze"
            className="px-3 py-1.5 rounded-lg bg-amber-500 text-slate-950 font-semibold text-xs hover:bg-amber-400 whitespace-nowrap"
          >
            Upload Real Resume
          </Link>
        </div>
      )}

      {/* Visual Analytics Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Coverage Gauge Doughnut */}
        <div className="lg:col-span-5">
          <Card
            title="Required Skill Coverage"
            subtitle="Deterministic mathematical partition"
            icon={PieIcon}
            className="h-full flex flex-col justify-between"
          >
            <div className="relative flex h-52 w-full items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gaugeData}
                    cx="50%"
                    cy="50%"
                    startAngle={90}
                    endAngle={-270}
                    innerRadius={65}
                    outerRadius={88}
                    dataKey="value"
                  >
                    {gaugeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-3xl font-black text-white">
                  {gapSummary.full_coverage_display || `${fullCovPct}%`}
                </span>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Full Coverage
                </span>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/50 p-3.5 text-center text-xs text-slate-300">
              <p>
                <strong className="text-emerald-400">
                  {gapSummary.matched_required_count ?? 0}
                </strong>{' '}
                of{' '}
                <strong className="text-white">
                  {gapSummary.total_required_count ?? 0}
                </strong>{' '}
                mandatory requirements evidenced
              </p>
              <div className="mt-2 flex justify-center gap-3 border-t border-slate-800/80 pt-2 text-[11px] text-slate-400">
                <span>
                  Full: <strong className="text-slate-200">{gapSummary.full_coverage_display || '75.0%'}</strong> ({gapSummary.fully_matched_required_count || 0} satisfied)
                </span>
                <span>&bull;</span>
                <span>
                  Any: <strong className="text-slate-200">{gapSummary.any_coverage_display || '87.5%'}</strong> ({gapSummary.matched_required_count || 0} evidenced)
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* Skill Evidence Breakdown Bar Chart */}
        <div className="lg:col-span-7">
          <Card
            title="Skill Evidence Breakdown"
            subtitle="Required vs preferred competency status"
            icon={BarChart3}
            className="h-full"
          >
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
                  <XAxis type="number" stroke="#64748B" fontSize={11} allowDecimals={false} />
                  <YAxis type="category" dataKey="category" stroke="#94A3B8" fontSize={11} width={120} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#334155',
                      borderRadius: '0.5rem',
                      color: '#F8FAFC',
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                    {barData.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </div>

      {/* Prioritized Roadmap & Partial Competencies */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Prioritized Skill Gap Roadmap */}
        <div className="lg:col-span-7">
          <Card
            title="Prioritized Skill Gap Roadmap"
            subtitle="Ranked by mandatory status and posting frequency"
            icon={ListOrdered}
            className="h-full"
            bodyClassName="p-0"
          >
            {prioritizedGaps.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/60 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-5 py-3">Skill</th>
                      <th className="px-5 py-3">Severity</th>
                      <th className="px-5 py-3">Requirement Type</th>
                      <th className="px-5 py-3">Mentions in Job</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {prioritizedGaps.map((gap: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-5 py-3.5 font-bold text-white capitalize">
                          {gap.skill || gap.skill_name}
                        </td>
                        <td className="px-5 py-3.5">
                          {String(gap.priority || gap.severity || '').includes('High') ? (
                            <Badge variant="rose" size="sm">High Priority</Badge>
                          ) : (
                            <Badge variant="amber" size="sm">Medium Priority</Badge>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
                            {gap.type || gap.importance || 'Mandatory'}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {gap.frequency_in_job || gap.jd_frequency || 1} time(s)
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-emerald-400">
                <CheckCircle2 className="mx-auto h-8 w-8 mb-2" />
                No skill gaps detected. Resume covers all required competencies!
              </div>
            )}
          </Card>
        </div>

        {/* Partially Evidenced Competencies */}
        <div className="lg:col-span-5">
          <Card
            title="Partially Evidenced Competencies"
            subtitle="Skills found in keyword lists without active project verbs"
            icon={HelpCircle}
            className="h-full"
          >
            {partialSkills.length > 0 ? (
              <div className="space-y-4">
                <p className="text-xs text-slate-300 leading-relaxed">
                  These skills appear in summary keyword lists but lack demonstrable project context or implementation verbs:
                </p>
                <div className="flex flex-wrap gap-2">
                  {partialSkills.map((s: string, idx: number) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400"
                    >
                      {s}
                      <HelpCircle className="h-3 w-3" />
                    </span>
                  ))}
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3.5 text-xs text-slate-400">
                  <strong className="text-slate-200">Optimization Tip:</strong> Add a bullet point describing how you implemented each skill with measurable metrics and architectural impact.
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center text-xs text-slate-400">
                <CheckCircle2 className="h-8 w-8 text-emerald-400 mb-2" />
                <span>All matched skills have contextual implementation evidence.</span>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Curated Learning Resources Grid */}
      <Card
        title="Curated Learning Resources for Gaps"
        subtitle="Verified official documentation for identified deficiencies"
        icon={BookOpen}
      >
        {(analysis.learning_resources || []).length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {(analysis.learning_resources || []).map((res: any, idx: number) => (
              <div
                key={idx}
                className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 transition"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <h5 className="font-bold text-sm text-indigo-400">{res.skill}</h5>
                    <Badge variant="slate" size="sm">{res.provider}</Badge>
                  </div>
                  {res.description && (
                    <p className="text-xs text-slate-300 leading-relaxed mb-4">{res.description}</p>
                  )}
                </div>
                <a
                  href={res.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-2 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 transition"
                >
                  <span>{res.title}</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 text-xs text-slate-400">
            Candidate covers all identified required competencies for this target position.
          </div>
        )}
      </Card>
    </div>
  );
};
