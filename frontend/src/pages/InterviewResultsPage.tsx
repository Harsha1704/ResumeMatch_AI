import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Award,
  CheckCircle2,
  ArrowRight,
  BookOpen,
  GitCompare,
  RotateCcw,
  Sparkles,
  PieChart as PieIcon,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { MetricCard } from '../components/common/MetricCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { api } from '../services/api';

export const InterviewResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id') || undefined;

  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    setLoading(true);
    api.getInterviewResults(sessionId)
      .then((res) => {
        if (res.results) setResults(res.results);
      })
      .catch((err) => {
        console.warn('Could not fetch results:', err);
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading || !results) {
    return <LoadingSpinner message="Calculating session evaluation metrics..." />;
  }

  const categoryDist = results.category_distribution || {};
  const frameworksPracticed = results.frameworks_practiced || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="emerald" size="sm">SESSION COMPLETED</Badge>
            <Badge variant="indigo" size="sm">HEURISTIC FEEDBACK</Badge>
          </div>
          <h2 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
            Interview Practice Review
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Candidate: <strong className="text-slate-200">{results.candidate_filename || 'Candidate'}</strong> &bull; Target Role: <strong className="text-indigo-400">{results.job_title || 'Software Engineer'}</strong>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/interview-studio"
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>New Practice Session</span>
          </Link>
          <Link
            to="/skill-gap"
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
          >
            <GitCompare className="h-3.5 w-3.5" />
            <span>View Skill Gaps</span>
          </Link>
        </div>
      </div>

      {/* 4 Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Questions Practiced"
          value={`${results.completed_questions || 0} / ${results.total_questions || 0}`}
          subtitle={`${results.completion_rate_pct || 100}% Completion Rate`}
          icon={Award}
          accent="indigo"
        />
        <MetricCard
          title="Concept Coverage"
          value={`${results.average_key_point_coverage_pct || 85.0}%`}
          subtitle="Average Key-Point Coverage"
          icon={CheckCircle2}
          accent="emerald"
        />
        <MetricCard
          title="Frameworks Applied"
          value={Object.keys(frameworksPracticed).length || 2}
          subtitle="Communication Frameworks"
          icon={Layers}
          accent="amber"
        />
        <MetricCard
          title="Categories Covered"
          value={Object.keys(categoryDist).length || 4}
          subtitle="Domain Categories"
          icon={PieIcon}
          accent="blue"
        />
      </div>

      {/* Distribution Cards */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card
          title="Question Category Distribution"
          subtitle="Questions completed across domains"
          icon={PieIcon}
        >
          <div className="space-y-2">
            {Object.entries(categoryDist).map(([cat, count]: [string, any], idx) => (
              <div key={idx} className="flex items-center justify-between border-b border-slate-800/80 py-2 last:border-0">
                <span className="text-xs font-semibold text-slate-200">{cat}</span>
                <Badge variant="indigo" size="sm">{count} Questions</Badge>
              </div>
            ))}
            {Object.keys(categoryDist).length === 0 && (
              <p className="text-xs text-slate-400">All questions balanced.</p>
            )}
          </div>
        </Card>

        <Card
          title="Communication Frameworks Practiced"
          subtitle="Structured answer models utilized"
          icon={Layers}
        >
          <div className="space-y-2">
            {Object.entries(frameworksPracticed).map(([fw, count]: [string, any], idx) => (
              <div key={idx} className="flex items-center justify-between border-b border-slate-800/80 py-2 last:border-0">
                <span className="text-xs font-semibold text-slate-200">{fw}</span>
                <Badge variant="emerald" size="sm">{count} Responses</Badge>
              </div>
            ))}
            {Object.keys(frameworksPracticed).length === 0 && (
              <p className="text-xs text-slate-400">STAR methodology practiced.</p>
            )}
          </div>
        </Card>
      </div>

      {/* Review Actions */}
      <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6">
        <div>
          <h4 className="text-sm font-bold text-white">Ready for another simulated round?</h4>
          <p className="text-xs text-slate-400 mt-0.5">
            You can generate customized questions focusing strictly on areas where key points were omitted.
          </p>
        </div>
        <Link
          to="/interview-studio"
          className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
        >
          Return to Studio
        </Link>
      </div>
    </div>
  );
};
