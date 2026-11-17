import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Award,
  CheckCircle2,
  GitCompare,
  RotateCcw,
  Sparkles,
  PieChart as PieIcon,
  Layers,
  ChevronDown,
  ChevronUp,
  ShieldAlert
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { MetricCard } from '../components/common/MetricCard';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { api } from '../services/api';

export const InterviewResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id') || undefined;

  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<any>(null);
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({});

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

  const toggleQuestionExpand = (num: number) => {
    setExpandedQuestions(prev => ({ ...prev, [num]: !prev[num] }));
  };

  if (loading || !results) {
    return <LoadingSpinner message="Calculating session evaluation metrics..." />;
  }

  const categoryDist = results.category_distribution || {};
  const frameworksPracticed = results.frameworks_practiced || {};
  const questionReviews = results.question_reviews || [];
  const averageScore = results.average_score ?? results.overall_score ?? 80.0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="emerald" size="sm">SESSION COMPLETED</Badge>
            <Badge variant="indigo" size="sm">DETERMINISTIC EVALUATION</Badge>
          </div>
          <h2 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
            Interview Practice Review &amp; Evaluation
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Candidate: <strong className="text-slate-200">{results.candidate_filename || 'Candidate'}</strong> &bull; Target Role: <strong className="text-indigo-400">{results.target_role || results.job_title || 'Software Engineer'}</strong>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
          title="Overall Heuristic Score"
          value={`${averageScore}%`}
          subtitle="Weighted across 6 criteria"
          icon={Award}
          accent={averageScore >= 70 ? 'emerald' : 'amber'}
        />
        <MetricCard
          title="Questions Practiced"
          value={`${results.completed_questions || 0} / ${results.total_questions || 0}`}
          subtitle={`${results.completion_rate_pct || 100}% Completion Rate`}
          icon={CheckCircle2}
          accent="indigo"
        />
        <MetricCard
          title="Concept Coverage"
          value={`${results.average_key_point_coverage_pct || 85.0}%`}
          subtitle="Average Key-Point Coverage"
          icon={Sparkles}
          accent="emerald"
        />
        <MetricCard
          title="Frameworks Applied"
          value={Object.keys(frameworksPracticed).length || 1}
          subtitle="Communication Models"
          icon={Layers}
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

      {/* Global Evidence Warnings (if any) */}
      {results.evidence_grounding_warnings && results.evidence_grounding_warnings.length > 0 && (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-5 space-y-2">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-300">
            <ShieldAlert className="h-5 w-5 text-amber-400" />
            <span>Evidence-Grounding Audit Alerts</span>
          </div>
          <p className="text-xs text-amber-200/80">
            The following claims were mentioned in your answers but do not match verified credentials in your uploaded resume:
          </p>
          <ul className="text-xs text-amber-200 pl-5 list-disc space-y-1">
            {results.evidence_grounding_warnings.map((w: string, idx: number) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Per-Question Detailed Reviews */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">
            Per-Question Review &amp; Criterion Breakdown ({questionReviews.length})
          </h3>
          <span className="text-xs text-slate-400">
            Click any question to expand full evaluation details
          </span>
        </div>

        {questionReviews.map((qr: any) => {
          const isExpanded = expandedQuestions[qr.number] ?? true;
          const ev = qr.evaluation;
          const qScore = ev?.overall_score ?? ev?.score ?? 0;

          return (
            <div
              key={qr.number}
              className="rounded-2xl border border-slate-800 bg-[#0F172A]/80 shadow-lg overflow-hidden transition"
            >
              {/* Question Header (Always Visible) */}
              <div
                onClick={() => toggleQuestionExpand(qr.number)}
                className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-800/40 select-none gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="indigo" size="sm">
                      Question {qr.number}
                    </Badge>
                    <Badge
                      variant={
                        qr.difficulty === 'Hard'
                          ? 'rose'
                          : qr.difficulty === 'Medium'
                          ? 'amber'
                          : 'emerald'
                      }
                      size="sm"
                    >
                      {qr.difficulty || 'Medium'}
                    </Badge>
                    {qr.related_skill && (
                      <span className="rounded bg-indigo-950 border border-indigo-700/60 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                        {qr.related_skill}
                      </span>
                    )}
                    <Badge variant={qr.is_answered ? 'emerald' : 'slate'} size="sm">
                      {qr.is_answered ? 'Answered' : 'Skipped'}
                    </Badge>
                  </div>
                  <h4 className="text-sm font-bold text-white leading-snug">
                    {qr.question_text}
                  </h4>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {qr.is_answered && (
                    <div className="text-right">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Score</span>
                      <span className={`text-base font-black ${
                        qScore >= 70 ? 'text-emerald-400' : qScore >= 50 ? 'text-amber-400' : 'text-rose-400'
                      }`}>
                        {qScore}%
                      </span>
                    </div>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-slate-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-slate-400" />
                  )}
                </div>
              </div>

              {/* Collapsible Details */}
              {isExpanded && (
                <div className="border-t border-slate-800/80 p-5 space-y-4 bg-slate-900/40">
                  {/* Candidate Answer */}
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                      Your Submitted Answer:
                    </span>
                    <p className="rounded-xl border border-slate-800 bg-[#0B1120] p-3.5 text-xs text-slate-200 leading-relaxed whitespace-pre-line">
                      {qr.user_answer || '(No answer provided for this question)'}
                    </p>
                  </div>

                  {/* 6 Individual Criterion Scores */}
                  {ev?.criterion_scores && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                        Criterion Scores Breakdown:
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {Object.entries(ev.criterion_scores).map(([k, crit]: [string, any]) => (
                          <div
                            key={k}
                            className="rounded-xl border border-slate-800 bg-[#0F172A] p-3 space-y-1"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-semibold text-slate-300 capitalize">
                                {k.replace('_', ' ')}
                              </span>
                              <span className={`font-bold ${crit.score >= 70 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                {crit.score}%
                              </span>
                            </div>
                            <ProgressBar percentage={crit.score} color={crit.score >= 70 ? 'emerald' : 'amber'} />
                            <p className="text-[10px] text-slate-400 line-clamp-2 mt-1">
                              {crit.details}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Strengths & Improvements */}
                  {ev && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {ev.strengths && ev.strengths.length > 0 && (
                        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block">
                            Key Strengths
                          </span>
                          <ul className="text-xs text-slate-300 space-y-0.5 pl-4 list-disc">
                            {ev.strengths.map((str: string, i: number) => (
                              <li key={i}>{str}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {(ev.improvement_suggestions || ev.areas_for_improvement) && (
                        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 space-y-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 block">
                            Recommended Improvements
                          </span>
                          <ul className="text-xs text-slate-300 space-y-0.5 pl-4 list-disc">
                            {(ev.improvement_suggestions || ev.areas_for_improvement || []).map((imp: string, i: number) => (
                              <li key={i}>{imp}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Review Actions Footer */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6 gap-4">
        <div>
          <h4 className="text-sm font-bold text-white">Continue Your Preparation</h4>
          <p className="text-xs text-slate-400 mt-0.5">
            You can return to the Interview Studio to practice other domains or review role-specific skill roadmaps.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/interview-studio"
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
          >
            Return to Studio
          </Link>
        </div>
      </div>
    </div>
  );
};
