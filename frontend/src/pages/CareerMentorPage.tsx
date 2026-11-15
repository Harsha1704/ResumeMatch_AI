import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  GraduationCap,
  Sparkles,
  Edit2,
  Check,
  X,
  ShieldCheck,
  Award,
  AlertTriangle,
  Calendar,
  Clock,
  ChevronDown,
  ChevronUp,
  Layers,
  ArrowRight,
  ExternalLink,
  BookOpen,
  CheckCircle2,
  ListTodo
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { MentorDossier, Roadmap } from '../types';

export const CareerMentorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlId = searchParams.get('id');
  const { currentAnalysis } = useAnalysis();

  const [dossier, setDossier] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Edit Name State
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState('');

  // Edit Role State
  const [isEditingRole, setIsEditingRole] = useState(false);
  const [roleInput, setRoleInput] = useState('');

  // Edit Education State
  const [isEditingEdu, setIsEditingEdu] = useState(false);
  const [eduInput, setEduInput] = useState('');

  // Expand states
  const [expandedCounseling, setExpandedCounseling] = useState<Record<string, boolean>>({});
  const [expandedRemaining, setExpandedRemaining] = useState(false);
  const [expandedRoadmaps, setExpandedRoadmaps] = useState<Record<string, boolean>>({});
  const [selectedCategory, setSelectedCategory] = useState('all');

  const fetchDossier = (aid?: string) => {
    setLoading(true);
    api.getCareerMentor(aid || currentAnalysis?.analysis_id || 'sample')
      .then((res) => {
        if (res.dossier) {
          setDossier(res.dossier);
          setNameInput(res.dossier.identity?.preferred_name || '');
          setRoleInput(res.dossier.target_role || '');
          setEduInput(res.dossier.identity?.education || '');
        }
      })
      .catch((err) => {
        console.warn('Career Mentor fetch error:', err);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDossier(urlId || currentAnalysis?.analysis_id);
  }, [urlId, currentAnalysis?.analysis_id]);

  if (loading || !dossier) {
    return <LoadingSpinner message="Assembling personalized career guidance dossier..." />;
  }

  const handleSaveName = async () => {
    if (!nameInput.trim()) return;
    try {
      await api.updateCandidateName(nameInput.trim());
      setIsEditingName(false);
      fetchDossier();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveRole = async () => {
    if (!roleInput.trim()) return;
    try {
      await api.updateCandidateRole(roleInput.trim());
      setIsEditingRole(false);
      fetchDossier();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveEdu = async () => {
    if (!eduInput.trim()) return;
    try {
      await api.confirmEducation(eduInput.trim());
      setIsEditingEdu(false);
      fetchDossier();
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleTask = async (taskKey: string, currentStatus: string) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    try {
      await api.updateMentorProgress(taskKey, newStatus);
      fetchDossier();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleCounseling = (idx: string) => {
    setExpandedCounseling(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleRoadmap = (slug: string) => {
    setExpandedRoadmaps(prev => ({ ...prev, [slug]: !prev[slug] }));
  };

  const expandAllRoadmaps = () => {
    const all: Record<string, boolean> = {};
    (dossier.roadmaps || []).forEach((rm: any) => {
      all[rm.skill_name] = true;
    });
    setExpandedRoadmaps(all);
  };

  const collapseAllRoadmaps = () => {
    setExpandedRoadmaps({});
  };

  const topGaps = dossier.gaps?.top_priorities || [];
  const expandableRequirements = dossier.gaps?.expandable_requirements || [];
  const progressSummary = dossier.progress_summary || {
    completed_tasks: 0,
    total_tasks: 12,
    completion_percentage: 0,
    disclaimer: 'Progress tracks self-reported completion of deterministic study milestones.',
  };

  return (
    <div className="space-y-6">
      {/* Mentor Hero Greeting Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-indigo-950/30 to-slate-900 p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
            <GraduationCap className="h-8 w-8" />
          </div>

          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="indigo" size="sm">PERSONALIZED MENTOR</Badge>
              <Badge variant="emerald" size="sm">100% DETERMINISTIC GUIDANCE</Badge>

              {/* Candidate Display Name Controls */}
              <div className="ml-auto flex items-center gap-2">
                {isEditingName ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                      placeholder="Candidate Name"
                    />
                    <button
                      onClick={handleSaveName}
                      className="rounded-md bg-emerald-600 p-1 text-white hover:bg-emerald-500"
                      title="Save Name"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setIsEditingName(false)}
                      className="rounded-md bg-slate-700 p-1 text-slate-300 hover:bg-slate-600"
                      title="Cancel"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Candidate:</span>
                    <strong className="text-xs text-white">
                      {dossier.identity?.preferred_name || 'Candidate'}
                    </strong>
                    <button
                      onClick={() => setIsEditingName(true)}
                      className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] text-slate-300 hover:bg-slate-700 hover:text-white"
                    >
                      <Edit2 className="h-2.5 w-2.5" />
                      <span>Edit</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            <h2 className="mt-2 text-2xl font-black tracking-tight text-white sm:text-3xl">
              {dossier.identity?.mentor_title || `${dossier.identity?.preferred_name || 'Candidate'}'s Career Mentor`}
            </h2>

            {/* Target Role & Education Row */}
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-300">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Target Role:</span>
                {isEditingRole ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={roleInput}
                      onChange={(e) => setRoleInput(e.target.value)}
                      className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs text-white focus:outline-none"
                    />
                    <button onClick={handleSaveRole} className="p-0.5 text-emerald-400 hover:text-emerald-300">
                      <Check className="h-3 w-3" />
                    </button>
                    <button onClick={() => setIsEditingRole(false)} className="p-0.5 text-slate-400 hover:text-white">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <strong className="text-indigo-300">{dossier.target_role || 'Target Position'}</strong>
                    <button
                      onClick={() => setIsEditingRole(true)}
                      className="text-[10px] text-slate-400 hover:text-white"
                    >
                      (change)
                    </button>
                  </div>
                )}
              </div>

              <span>&bull;</span>

              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Education:</span>
                {isEditingEdu ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={eduInput}
                      onChange={(e) => setEduInput(e.target.value)}
                      className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs text-white focus:outline-none"
                    />
                    <button onClick={handleSaveEdu} className="p-0.5 text-emerald-400 hover:text-emerald-300">
                      <Check className="h-3 w-3" />
                    </button>
                    <button onClick={() => setIsEditingEdu(false)} className="p-0.5 text-slate-400 hover:text-white">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <strong className="text-slate-200">
                      {dossier.identity?.education || 'Degree qualification confirmed'}
                    </strong>
                    <button
                      onClick={() => setIsEditingEdu(true)}
                      className="text-[10px] text-slate-400 hover:text-white"
                    >
                      (confirm)
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Personalized Chat Greeting Bubble */}
        <div className="mt-6 rounded-xl border border-indigo-500/20 bg-slate-900/80 p-4 text-xs text-slate-300">
          <p className="leading-relaxed">{dossier.welcome_greeting}</p>
          <div className="mt-2 flex items-center gap-2 font-semibold text-amber-400">
            <Sparkles className="h-4 w-4" />
            <span>{dossier.encouragement_message}</span>
          </div>
        </div>
      </div>

      {/* Methodology Transparency Notice */}
      <div className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-xs text-slate-400">
        <ShieldCheck className="h-5 w-5 shrink-0 text-indigo-400" />
        <div>
          <strong className="text-slate-200 uppercase tracking-wide">Methodology Transparency: Deterministic Career Guidance</strong>
          <p className="mt-0.5 leading-relaxed">
            Career Mentor roadmaps, action plans, skill gap prioritization, and practical exercises are created using deterministic curricula and rule-based scheduling without generative AI hallucinations. Global match alignment indicators are driven by our evaluated Supervised ML classifier.
          </p>
        </div>
      </div>

      {/* Progress Tracker Overview Card */}
      <Card
        title="Preparation Progress Tracker"
        subtitle="Track deliberate study milestones across prioritized technical topics"
        icon={ListTodo}
        badge={
          <Badge variant="indigo" size="sm">
            {progressSummary.completion_percentage}% Done
          </Badge>
        }
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Milestones Completed:</span>
            <span className="font-bold text-emerald-400">
              {progressSummary.completed_tasks} / {progressSummary.total_tasks}
            </span>
          </div>
          <ProgressBar percentage={progressSummary.completion_percentage} color="emerald" />
          <p className="text-[11px] text-slate-400 italic">
            {progressSummary.disclaimer}
          </p>
        </div>
      </Card>

      {/* Section 1: Candidate Strengths */}
      <Card
        title={`Verified Candidate Strengths (${dossier.strengths?.total_skills || 0})`}
        subtitle="Technical competencies and experiences verified from resume"
        icon={Award}
      >
        <div className="space-y-4">
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Verified Technical Skills:
            </h4>
            <div className="flex flex-wrap gap-2">
              {(dossier.strengths?.verified_skills || []).map((sk: string, idx: number) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400"
                >
                  <CheckCircle2 className="h-3 w-3" />
                  {sk}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 pt-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Verified Projects ({dossier.strengths?.projects_count || 0})
              </h5>
              <div className="space-y-3">
                {(dossier.strengths?.projects || []).map((p: any, idx: number) => (
                  <div key={idx} className="border-b border-slate-800/80 pb-2 last:border-0 last:pb-0">
                    <strong className="text-xs text-white block">{p.title}</strong>
                    {p.technologies && (
                      <span className="text-[11px] text-slate-400">
                        Tech Stack: {p.technologies.join(', ')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Verified Internships ({dossier.strengths?.internships_count || 0})
              </h5>
              <div className="space-y-3">
                {(dossier.strengths?.internships || []).map((it: any, idx: number) => (
                  <div key={idx} className="border-b border-slate-800/80 pb-2 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between">
                      <strong className="text-xs text-white">{it.organization}</strong>
                      <span className="text-[10px] text-slate-400">{it.dates}</span>
                    </div>
                    {it.responsibilities && (
                      <p className="mt-1 text-[11px] text-slate-400 line-clamp-2">
                        {it.responsibilities.join('; ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Section 2: Prioritized Skill Gaps */}
      <Card
        title="Prioritized Technical &amp; Professional Skill Gaps"
        subtitle="Multi-factor priority ranking based on JD frequency, prerequisite readiness, and role relevance"
        icon={AlertTriangle}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
              Top 5 Immediate Priorities (Focus First)
            </span>
            <span className="text-[11px] text-slate-400">
              Ranked by prerequisite readiness
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {topGaps.map((gap: any, idx: number) => {
              const cpKey = `top_${idx}`;
              const isCpOpen = !!expandedCounseling[cpKey];
              return (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2.5 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-slate-300">
                        {idx + 1}
                      </span>
                      <h4 className="text-sm font-bold text-white">{gap.skill_name}</h4>
                    </div>
                    <Badge variant={gap.priority_tier === 'Mandatory' ? 'rose' : 'amber'} size="sm">
                      {gap.priority_tier}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                      {gap.category}
                    </span>
                    <span className="rounded bg-indigo-500/10 text-indigo-400 px-2 py-0.5 text-[10px]">
                      {gap.evidence_status}
                    </span>
                  </div>

                  <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 text-xs space-y-1.5 text-slate-300">
                    <p><strong className="text-indigo-400">Why Selected:</strong> {gap.priority_reason}</p>
                    {gap.jd_sentence && (
                      <p className="italic text-slate-400">"{gap.jd_sentence}"</p>
                    )}
                    <p><strong className="text-emerald-400">Recommended Action:</strong> {gap.recommended_action}</p>
                    {gap.practical_deliverable && (
                      <p><strong className="text-amber-400">Practical Deliverable:</strong> {gap.practical_deliverable}</p>
                    )}

                    {/* 9-Point Counseling Profile Accordion */}
                    {gap.counseling_profile && (
                      <div className="pt-2 border-t border-slate-800">
                        <button
                          type="button"
                          onClick={() => toggleCounseling(cpKey)}
                          className="flex items-center justify-between w-full text-indigo-400 text-xs font-semibold hover:text-indigo-300"
                        >
                          <span>9-Point Counseling Assessment</span>
                          {isCpOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                        {isCpOpen && (
                          <div className="mt-2 space-y-1.5 text-[11px] text-slate-400 border-l-2 border-indigo-500/40 pl-3">
                            <p><strong>1. Why It Matters:</strong> {gap.counseling_profile.q1_why_it_matters}</p>
                            <p><strong>2. Foundations:</strong> {gap.counseling_profile.q2_candidate_foundations}</p>
                            <p><strong>3. Demonstration Gap:</strong> {gap.counseling_profile.q3_demonstration_gap}</p>
                            <p><strong>4. Learn First:</strong> <span className="text-indigo-300">{gap.counseling_profile.q4_initial_learning_step}</span></p>
                            <p><strong>5. Practice Next:</strong> {gap.counseling_profile.q5_practical_exercise_step}</p>
                            <p><strong>6. Deliverable:</strong> <span className="text-emerald-300">{gap.counseling_profile.q6_practical_deliverable}</span></p>
                            <p><strong>7. Verification:</strong> {gap.counseling_profile.q7_verification_method}</p>
                            <p><strong>8. Interview Talking Point:</strong> <span className="italic text-slate-200">"{gap.counseling_profile.q8_interview_talking_point}"</span></p>
                            <p><strong>9. Resume Bullet:</strong> {gap.counseling_profile.q9_resume_bullet_guidance}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Expandable Remaining Requirements */}
          {expandableRequirements.length > 0 && (
            <div className="pt-4 text-center">
              <button
                type="button"
                onClick={() => setExpandedRemaining(!expandedRemaining)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
              >
                <span>{expandedRemaining ? 'Hide' : 'Show'} {expandableRequirements.length} Additional Requirements</span>
                {expandedRemaining ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {expandedRemaining && (
                <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 text-left">
                  {expandableRequirements.map((gap: any, idx: number) => (
                    <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <h5 className="font-bold text-white text-xs">{gap.skill_name}</h5>
                        <Badge variant="slate" size="sm">{gap.priority_tier}</Badge>
                      </div>
                      <p className="text-xs text-slate-400">{gap.priority_reason}</p>
                      <p className="text-xs text-emerald-400">{gap.recommended_action}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Section 3: Step-by-Step Learning Roadmaps */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-bold text-white">
            Step-by-Step Learning Roadmaps
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={expandAllRoadmaps}
              className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Expand All
            </button>
            <button
              onClick={collapseAllRoadmaps}
              className="rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
            >
              Collapse All
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {(dossier.roadmaps || []).map((rm: any, idx: number) => {
            const isOpen = !!expandedRoadmaps[rm.skill_name];
            return (
              <div
                key={idx}
                className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]/80 shadow-md"
              >
                <button
                  type="button"
                  onClick={() => toggleRoadmap(rm.skill_name)}
                  className="flex w-full items-center justify-between p-4 text-left hover:bg-slate-900/60 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-xs font-bold text-indigo-400 border border-indigo-500/20">
                      {idx + 1}
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-white">{rm.skill_name}</h4>
                      <p className="text-[11px] text-slate-400">
                        {rm.category} &bull; {rm.total_estimated_hours || 8} hrs estimated
                      </p>
                    </div>
                  </div>
                  {isOpen ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                </button>

                {isOpen && (
                  <div className="border-t border-slate-800 p-4 space-y-3 bg-slate-900/30">
                    {(rm.milestones || []).map((m: any, mIdx: number) => {
                      const isCompleted = m.completed || m.status === 'completed';
                      return (
                        <div
                          key={mIdx}
                          className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3"
                        >
                          <input
                            type="checkbox"
                            checked={isCompleted}
                            onChange={() => handleToggleTask(m.task_key, isCompleted ? 'completed' : 'pending')}
                            className="mt-1 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                          />
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <h5 className={`text-xs font-bold ${isCompleted ? 'text-slate-400 line-through' : 'text-slate-100'}`}>
                                Step {m.step_number}: {m.step_title}
                              </h5>
                              <span className="text-[10px] text-slate-400">
                                ~{m.estimated_hours || 2} hrs
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-slate-400">{m.milestone_description}</p>
                            {m.key_deliverable && (
                              <p className="mt-1 text-[11px] text-emerald-400">
                                <strong>Deliverable:</strong> {m.key_deliverable}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
