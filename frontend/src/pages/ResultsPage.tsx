import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Copy,
  Printer,
  GitCompare,
  FileText,
  Briefcase,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ExternalLink,
  Kanban,
  Calendar,
  Layers,
  GraduationCap,
  Lightbulb,
  BookOpen,
  Cpu,
  ShieldCheck,
  Zap,
  Info
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { MultiClassProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { AnalysisResult } from '../types';

export const ResultsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlId = searchParams.get('id');
  const { currentAnalysis, loadAnalysis, isLoading } = useAnalysis();

  const [copied, setCopied] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(currentAnalysis);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (urlId && urlId !== analysis?.analysis_id) {
      setFetching(true);
      api.getAnalysis(urlId)
        .then((res) => {
          if (res.analysis) setAnalysis(res.analysis);
        })
        .catch(() => {
          // fallback to active
          loadAnalysis(urlId).then((res) => {
            if (res) setAnalysis(res);
          });
        })
        .finally(() => setFetching(false));
    } else if (!analysis && currentAnalysis) {
      setAnalysis(currentAnalysis);
    }
  }, [urlId, currentAnalysis, analysis, loadAnalysis]);

  if (isLoading || fetching || !analysis) {
    return <LoadingSpinner message="Retrieving compatibility assessment..." />;
  }

  const handleCopyId = () => {
    navigator.clipboard.writeText(analysis.analysis_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const rawGap = analysis.skill_gap_summary || ({} as any);
  const fullCov = rawGap.full_coverage_display || `${rawGap.full_coverage_pct || 0}%`;
  const anyCov = rawGap.any_coverage_display || `${rawGap.any_coverage_pct || 0}%`;

  const projectsList = analysis.projects || (analysis as any).relevant_projects || [];
  const internshipsList = analysis.internships || [];

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 no-print">
        <div className="flex items-center gap-3">
          <Link
            to="/analyze"
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Analyzer</span>
          </Link>
          <Badge variant="slate" size="sm">
            Analysis ID: {analysis.analysis_id.slice(0, 8)}...
          </Badge>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleCopyId}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
          >
            <Copy className="h-3.5 w-3.5" />
            <span>{copied ? 'Copied!' : 'Copy ID'}</span>
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-medium text-indigo-300 hover:bg-indigo-500/20"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>Print Report</span>
          </button>
          <Link
            to={`/skill-gap?id=${encodeURIComponent(analysis.analysis_id)}`}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
          >
            <GitCompare className="h-3.5 w-3.5" />
            <span>Skill Gap Dashboard</span>
          </Link>
        </div>
      </div>

      {/* Header Summary Card */}
      <Card className="border-slate-800 bg-[#0F172A]/90 p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-center">
          <div className="lg:col-span-7">
            <Badge variant="indigo" size="sm" className="mb-2">
              TARGET POSITION
            </Badge>
            <h2 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
              {analysis.job_title || 'Target Job Position'}
            </h2>
            {analysis.target_role_source === 'user_override' && (
              <p className="mt-1 text-xs text-amber-300/80">
                Target role entered by user. Skill requirements and ML prediction remain based on the supplied job description.
                {analysis.detected_job_title && (
                  <span className="block text-slate-400">
                    Title detected from job description: {analysis.detected_job_title}
                  </span>
                )}
              </p>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <FileText className="h-3.5 w-3.5 text-slate-500" />
                Parsed: <strong className="text-slate-300">{analysis.filename || 'Resume'}</strong>
              </span>
              <span>&bull;</span>
              <span>
                Experience: <strong className="text-slate-300">{analysis.experience_analysis?.display_summary || analysis.experience_summary?.display_summary || 'Evaluated'}</strong>
              </span>
            </div>
          </div>

          {/* Supervised ML Prediction Badge */}
          <div className="lg:col-span-5 flex flex-col items-start lg:items-end">
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 text-center w-full sm:w-auto">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                Supervised ML Prediction
              </span>
              <div className="inline-block">
                {analysis.predicted_class === 'Good Fit' ? (
                  <span className="inline-flex items-center gap-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 px-5 py-2.5 text-lg font-black text-emerald-400 shadow-lg shadow-emerald-500/20">
                    <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                    Good Fit
                  </span>
                ) : analysis.predicted_class === 'Potential Fit' ? (
                  <span className="inline-flex items-center gap-2 rounded-xl bg-amber-500/20 border border-amber-500/40 px-5 py-2.5 text-lg font-black text-amber-400 shadow-lg shadow-amber-500/20">
                    <AlertTriangle className="h-6 w-6 text-amber-400" />
                    Potential Fit
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2 rounded-xl bg-rose-500/20 border border-rose-500/40 px-5 py-2.5 text-lg font-black text-rose-400 shadow-lg shadow-rose-500/20">
                    <XCircle className="h-6 w-6 text-rose-400" />
                    No Fit
                  </span>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Confidence: <strong className="text-slate-200">{analysis.model_confidence}%</strong> (Softmax)
              </p>
              <div className="mt-2 flex flex-wrap justify-center gap-1.5">
                {analysis.fallback_triggered ? (
                  <Badge variant="amber" size="sm">
                    Fallback to Baseline
                  </Badge>
                ) : analysis.is_challenger ? (
                  <Badge variant="amber" size="sm">
                    <Zap className="h-3 w-3" /> Challenger Model 5
                  </Badge>
                ) : (
                  <Badge variant="slate" size="sm">
                    <ShieldCheck className="h-3 w-3 text-emerald-400" /> Production Baseline
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Quantitative Overview KPI Row */}
        <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-800/80 pt-6 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Compatibility Score
            </span>
            <div className="mt-1 text-2xl font-black text-indigo-400">
              {analysis.compatibility_score}%
            </div>
            <span className="mt-0.5 block text-[10px] text-slate-400">
              Model match indicator (not hiring odds)
            </span>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Full Skill Coverage
            </span>
            <div className="mt-1 text-2xl font-black text-emerald-400">
              {fullCov}
            </div>
            <span className="mt-0.5 block text-[10px] text-slate-400">
              {rawGap.total_required_count > 0
                ? `${rawGap.fully_matched_required_count || 0} / ${rawGap.total_required_count} fully satisfied`
                : 'No mandatory requirements'}
            </span>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Any-Evidence Coverage
            </span>
            <div className="mt-1 text-2xl font-black text-slate-200">
              {anyCov}
            </div>
            <span className="mt-0.5 block text-[10px] text-slate-400">
              {rawGap.total_required_count > 0
                ? `${rawGap.matched_required_count || 0} / ${rawGap.total_required_count} evidenced`
                : 'Fully evidenced'}
            </span>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Experience Alignment
            </span>
            <div className="mt-1 text-sm font-bold text-slate-200 truncate">
              {analysis.experience_analysis?.display_summary || '1+ Internships'}
            </div>
            <span className="mt-0.5 block text-[10px] text-emerald-400">
              {analysis.experience_analysis?.meets_requirement ? 'Meets Requirement' : 'Aligned'}
            </span>
          </div>
        </div>

        {/* 3-Class Probability Bar */}
        <div className="mt-6 border-t border-slate-800/80 pt-6">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-bold uppercase tracking-wider">
              Supervised Model-Estimated Class Probabilities
            </span>
            <span>Softmax Cross-Entropy</span>
          </div>
          <MultiClassProgressBar probabilities={analysis.class_probabilities} />
        </div>

        {/* Methodology Transparency Notice */}
        <div className="mt-6 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-xs text-slate-400">
          <div className="flex items-center gap-2 font-bold text-slate-300 uppercase tracking-wider">
            <ShieldCheck className="h-4 w-4 text-indigo-400" />
            <span>Model Architecture: {analysis.model_used}</span>
          </div>
          <p className="mt-1.5 leading-relaxed">
            {analysis.calibration_note || 'Probabilities reflect trained scikit-learn classifier based on dual text and structured feature embeddings.'}
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            <strong>Note on Probability Interpretation:</strong> Model probabilities represent softmax cross-entropy outputs indicating directional algorithmic affinity, not verified real-world hiring guarantees. Deterministic NLP governs skill gaps and verified curricula without generative AI hallucination.
          </p>
        </div>
      </Card>

      {/* Skills Breakdown Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Matched Competencies */}
        <Card
          title={`Matched Competencies (${analysis.matched_skills.length})`}
          icon={CheckCircle2}
          badge={
            <Badge variant="emerald" size="sm">
              {rawGap.matched_required_count || 0} Required Met
            </Badge>
          }
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Mandatory Skills Evidenced ({analysis.matched_required_skills?.length || 0}):
              </h4>
              <div className="flex flex-wrap gap-2">
                {(analysis.matched_required_skills || []).map((skill, idx) => {
                  const isPartial = (analysis.partially_evidenced_required_skills || []).includes(skill);
                  return (
                    <span
                      key={idx}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium border ${
                        isPartial
                          ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                          : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                      }`}
                    >
                      {skill}
                      {isPartial ? (
                        <span title="Mentioned in list; lacks project verbs">
                          <HelpCircle className="h-3 w-3 text-amber-400" />
                        </span>
                      ) : (
                        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      )}
                    </span>
                  );
                })}
                {(!analysis.matched_required_skills || analysis.matched_required_skills.length === 0) && (
                  <span className="text-xs text-slate-400">None identified</span>
                )}
              </div>
            </div>

            {(analysis.matched_preferred_skills || []).length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Preferred / Bonus Skills Evidenced ({analysis.matched_preferred_skills?.length}):
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.matched_preferred_skills?.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400"
                    >
                      {skill}
                      <span className="rounded bg-blue-500/20 px-1 py-0.2 text-[9px] font-bold">Bonus</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Missing Skill Evidence */}
        <Card
          title={`Missing Skill Evidence (${analysis.missing_skills.length})`}
          icon={AlertTriangle}
          badge={
            <Badge variant="rose" size="sm">
              {rawGap.missing_required_count || 0} Required
            </Badge>
          }
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Mandatory Gaps ({analysis.missing_required_skills?.length || 0}):
              </h4>
              <div className="flex flex-wrap gap-2">
                {(analysis.missing_required_skills || []).map((skill, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-400"
                  >
                    {skill}
                    <span className="rounded bg-rose-500/20 px-1 py-0.2 text-[9px] font-bold">Required</span>
                  </span>
                ))}
                {(!analysis.missing_required_skills || analysis.missing_required_skills.length === 0) && (
                  <span className="text-xs font-semibold text-emerald-400">
                    No mandatory skill gaps!
                  </span>
                )}
              </div>
            </div>

            {(analysis.missing_preferred_skills || []).length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Preferred / Nice-to-Have Gaps ({analysis.missing_preferred_skills?.length}):
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.missing_preferred_skills?.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400"
                    >
                      {skill}
                      <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px]">Preferred</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
            <p className="text-[11px] italic text-slate-400">
              Note: Missing evidence indicates these skills were not detected in document text; it is not proof that the candidate cannot perform them.
            </p>
          </div>
        </Card>
      </div>

      {/* Practical Evidence: Projects & Internships */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Identified Projects */}
        <Card
          title={`Identified Projects (${projectsList.length})`}
          subtitle="Technical project evidence extracted from resume"
          icon={Kanban}
        >
          {projectsList.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-800">
              {projectsList.map((proj: any, idx: number) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <div className="flex items-start justify-between">
                    <h5 className="font-bold text-slate-100 text-sm">{proj.title || proj.project_title}</h5>
                    {proj.dates && (
                      <Badge variant="slate" size="sm">
                        <Calendar className="h-3 w-3" />
                        {proj.dates}
                      </Badge>
                    )}
                  </div>
                  {proj.description && (
                    <p className="mt-2 text-xs text-slate-300 leading-relaxed">{proj.description}</p>
                  )}
                  {proj.technologies && proj.technologies.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {proj.technologies.map((t: string, i: number) => (
                        <span
                          key={i}
                          className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">
              No structured project blocks identified.
            </p>
          )}
        </Card>

        {/* Internships & Practical Experience */}
        <Card
          title={`Internships & Practical Experience (${internshipsList.length})`}
          subtitle="Industry training and experiential verification"
          icon={Briefcase}
        >
          {internshipsList.length > 0 ? (
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-800">
              {internshipsList.map((intern: any, idx: number) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h5 className="font-bold text-slate-100 text-sm">{intern.organization}</h5>
                      {intern.position && (
                        <p className="text-xs font-medium text-indigo-400">{intern.position}</p>
                      )}
                    </div>
                    {intern.dates && (
                      <Badge variant="slate" size="sm">
                        <Calendar className="h-3 w-3" />
                        {intern.dates}
                      </Badge>
                    )}
                  </div>
                  {intern.responsibilities && intern.responsibilities.length > 0 && (
                    <ul className="mt-2 list-disc pl-4 text-xs text-slate-300 space-y-1">
                      {intern.responsibilities.map((r: string, i: number) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                  {intern.technologies && intern.technologies.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {intern.technologies.map((t: string, i: number) => (
                        <span
                          key={i}
                          className="rounded bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[11px] text-indigo-300"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">
              No internships identified in the uploaded resume.
            </p>
          )}
        </Card>
      </div>

      {/* Recommendations & Verified Learning Resources */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recommendations */}
        <Card
          title="Resume Improvement Recommendations"
          subtitle="Targeted action items for maximizing compatibility"
          icon={Lightbulb}
        >
          {(analysis.recommendations || []).length > 0 ? (
            <div className="space-y-3">
              {(analysis.recommendations || []).map((rec: any, idx: number) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge
                      variant={
                        rec.severity === 'danger' || rec.severity === 'critical'
                          ? 'rose'
                          : rec.severity === 'warning'
                          ? 'amber'
                          : 'indigo'
                      }
                      size="sm"
                    >
                      {rec.category}
                    </Badge>
                  </div>
                  <h5 className="text-xs font-bold text-slate-100">{rec.action || rec.recommendation}</h5>
                  <p className="mt-1 text-xs text-slate-400">{rec.rationale || rec.actionable_step}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No critical resume adjustments flagged.</p>
          )}
        </Card>

        {/* Learning Resources */}
        <Card
          title="Curated Learning Resources"
          subtitle="Official documentation for identified gaps"
          icon={BookOpen}
        >
          {(analysis.learning_resources || []).length > 0 ? (
            <div className="space-y-3">
              {(analysis.learning_resources || []).map((res: any, idx: number) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-400">{res.skill}</span>
                    <span className="text-[11px] text-slate-400">{res.provider}</span>
                  </div>
                  {res.description && (
                    <p className="mt-1 text-xs text-slate-300">{res.description}</p>
                  )}
                  <div className="mt-2.5">
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                    >
                      <span>Official Documentation: {res.title}</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">
              All mandatory skills are evidenced or documentation was already consulted.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
};
