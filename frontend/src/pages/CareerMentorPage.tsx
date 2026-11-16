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
  ListTodo,
  Briefcase,
  Target,
  TrendingUp,
  FileText,
  User
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { MentorDossier } from '../types';

export const CareerMentorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlId = searchParams.get('id');
  const { currentAnalysis } = useAnalysis();

  const [dossier, setDossier] = useState<MentorDossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'roles' | 'gaps' | 'roadmaps' | 'recommendations'>('overview');

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
  const [expandedRoadmaps, setExpandedRoadmaps] = useState<Record<string, boolean>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>('all');

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

  const careerProfile = dossier.career_profile;
  const recommendedRoles = dossier.recommended_roles || [];
  const resumeSuggestions = dossier.resume_improvement_suggestions || [];
  const careerRoadmap = dossier.career_roadmap;
  const progressSummary = dossier.progress_summary || {
    completed_tasks: 0,
    total_tasks: 12,
    completion_percentage: 0,
    disclaimer: 'Progress tracks self-reported completion of deterministic study milestones.',
  };

  // Filter gaps by category
  const allPrioritized = dossier.gaps?.prioritized_gaps || [];
  const filteredGaps = selectedCategory === 'all'
    ? allPrioritized
    : allPrioritized.filter((g: any) => g.category === selectedCategory);

  // Filter roles by fit tier
  const filteredRoles = selectedRoleFilter === 'all'
    ? recommendedRoles
    : recommendedRoles.filter((r: any) => r.fit_tier === selectedRoleFilter);

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
              <Badge variant="indigo" size="sm">EVIDENCE-GROUNDED MENTOR</Badge>
              <Badge variant="emerald" size="sm">DETERMINISTIC REASONING</Badge>

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
                      className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs text-white"
                      placeholder="Target Role"
                    />
                    <button onClick={handleSaveRole} className="text-emerald-400 hover:text-emerald-300"><Check className="h-3 w-3" /></button>
                    <button onClick={() => setIsEditingRole(false)} className="text-slate-400 hover:text-slate-300"><X className="h-3 w-3" /></button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <strong className="text-white">{dossier.target_role || 'Target Technical Position'}</strong>
                    <button onClick={() => setIsEditingRole(true)} className="text-slate-400 hover:text-white">
                      <Edit2 className="h-2.5 w-2.5" />
                    </button>
                  </div>
                )}
              </div>

              <span className="text-slate-600">&bull;</span>

              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Education:</span>
                {isEditingEdu ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={eduInput}
                      onChange={(e) => setEduInput(e.target.value)}
                      className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs text-white"
                      placeholder="Degree & Major"
                    />
                    <button onClick={handleSaveEdu} className="text-emerald-400 hover:text-emerald-300"><Check className="h-3 w-3" /></button>
                    <button onClick={() => setIsEditingEdu(false)} className="text-slate-400 hover:text-slate-300"><X className="h-3 w-3" /></button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-200">{dossier.identity?.education || 'Not specified'}</span>
                    <button onClick={() => setIsEditingEdu(true)} className="text-slate-400 hover:text-white">
                      <Edit2 className="h-2.5 w-2.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-slate-300">
              {dossier.welcome_greeting}
            </p>
          </div>
        </div>

        {/* Progress Tracker Bar */}
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-bold text-white">Study Roadmap Completion</span>
            </div>
            <span className="text-xs font-semibold text-emerald-400">
              {progressSummary.completed_tasks} of {progressSummary.total_tasks} milestones finished ({progressSummary.completion_percentage ?? progressSummary.percentage ?? 0}%)
            </span>
          </div>
          <div className="mt-2">
            <ProgressBar percentage={progressSummary.completion_percentage ?? progressSummary.percentage ?? 0} color="emerald" />
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            {progressSummary.disclaimer || 'Tracks self-reported milestone completion for grounded technical preparation.'}
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeTab === 'overview'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
              : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <User className="h-3.5 w-3.5" />
          <span>Career Profile</span>
        </button>

        <button
          onClick={() => setActiveTab('roles')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeTab === 'roles'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
              : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <Target className="h-3.5 w-3.5" />
          <span>Recommended Roles</span>
          {recommendedRoles.length > 0 && (
            <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300">
              {recommendedRoles.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('gaps')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeTab === 'gaps'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
              : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Skill-Gap Intelligence</span>
          {allPrioritized.length > 0 && (
            <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300">
              {allPrioritized.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('roadmaps')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeTab === 'roadmaps'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
              : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span>Learning Roadmaps</span>
        </button>

        <button
          onClick={() => setActiveTab('recommendations')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeTab === 'recommendations'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25'
              : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <TrendingUp className="h-3.5 w-3.5" />
          <span>Actionable Guidance</span>
        </button>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: CAREER PROFILE OVERVIEW                                      */}
      {/* =================================================================== */}
      {activeTab === 'overview' && careerProfile && (
        <div className="space-y-6">
          {/* Identity & Contact Cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card className="p-4 space-y-2 border-slate-800 bg-[#0F172A]/90">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                <User className="h-4 w-4 text-indigo-400" />
                <span>Contact Verification</span>
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Email:</span>
                  <span className="font-mono text-slate-200">{careerProfile.identity.email || 'Not provided'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Phone:</span>
                  <span className="text-slate-200">{careerProfile.identity.phone || 'Not provided'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Location:</span>
                  <span className="text-slate-200">{careerProfile.identity.location}</span>
                </div>
              </div>
              <div className="pt-2 flex flex-wrap gap-2 border-t border-slate-800/80">
                {careerProfile.identity.has_github ? (
                  <Badge variant="emerald" size="sm">GitHub Linked</Badge>
                ) : (
                  <Badge variant="amber" size="sm">GitHub Missing</Badge>
                )}
                {careerProfile.identity.has_linkedin ? (
                  <Badge variant="indigo" size="sm">LinkedIn Linked</Badge>
                ) : (
                  <Badge variant="slate" size="sm">LinkedIn Omitted</Badge>
                )}
              </div>
            </Card>

            <Card className="p-4 space-y-2 border-slate-800 bg-[#0F172A]/90">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                <GraduationCap className="h-4 w-4 text-emerald-400" />
                <span>Education Credentials</span>
              </div>
              {careerProfile.education.records.length > 0 ? (
                <div className="space-y-2">
                  {careerProfile.education.records.map((edu: any, i: number) => (
                    <div key={i} className="text-xs">
                      <div className="font-bold text-white">{edu.degree_name}</div>
                      <div className="text-slate-400 text-[11px]">{edu.institution} {edu.graduation_year ? `(${edu.graduation_year})` : ''}</div>
                    </div>
                  ))}
                  <div className="pt-1">
                    <Badge variant={careerProfile.education.education_verified ? 'emerald' : 'slate'} size="sm">
                      Status: {careerProfile.education.verification_status}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-400">No formal education credentials documented in resume.</div>
              )}
            </Card>

            <Card className="p-4 space-y-2 border-slate-800 bg-[#0F172A]/90">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                <Briefcase className="h-4 w-4 text-purple-400" />
                <span>Experience Scope</span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-300">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Total Experience:</span>
                  <span className="font-bold text-white">{careerProfile.experience.total_experience_years} years</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Documented Projects:</span>
                  <span className="text-slate-200">{careerProfile.experience.projects_count} projects</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Internships:</span>
                  <span className="text-slate-200">{careerProfile.experience.internships_count} recorded</span>
                </div>
              </div>
              <p className="pt-1 text-[11px] text-slate-400 italic">
                {careerProfile.experience.display_summary}
              </p>
            </Card>
          </div>

          {/* Competencies Categorization (Demonstrated vs Confirmed vs Partial) */}
          <Card className="p-6 border-slate-800 bg-[#0F172A]/90 space-y-6">
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">Verified Competencies Evidence</h3>
                  <p className="text-xs text-slate-400">Strictly grounded in resume documents and explicit candidate attestations.</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span> Resume-Demonstrated
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-purple-400 font-medium ml-3">
                    <span className="h-2 w-2 rounded-full bg-purple-500"></span> Candidate-Confirmed
                  </span>
                </div>
              </div>

              {/* Demonstrated Skills */}
              <div className="mt-4 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                  Resume-Demonstrated Competencies ({careerProfile.demonstrated_competencies.length})
                </h4>
                {careerProfile.demonstrated_competencies.length > 0 ? (
                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                    {careerProfile.demonstrated_competencies.map((comp: any, idx: number) => (
                      <div key={idx} className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-white">{comp.skill}</span>
                          <span className="text-[10px] text-emerald-400 font-mono">{(comp.confidence * 100).toFixed(0)}% conf</span>
                        </div>
                        <p className="text-[11px] text-slate-300 line-clamp-2">{comp.excerpt}</p>
                        <div className="text-[10px] text-slate-400 italic">Source: {comp.provenance_title}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-400">
                    No skills with verifiable project or internship implementation descriptions found.
                  </div>
                )}
              </div>

              {/* Candidate-Confirmed Skills */}
              {careerProfile.candidate_confirmed_competencies.length > 0 && (
                <div className="mt-6 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">
                    Candidate Self-Confirmed ({careerProfile.candidate_confirmed_competencies.length})
                  </h4>
                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                    {careerProfile.candidate_confirmed_competencies.map((comp: any, idx: number) => (
                      <div key={idx} className="rounded-xl border border-purple-900/40 bg-purple-950/20 p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-white">{comp.skill}</span>
                          <span className="text-[10px] text-purple-400 font-mono">Self-Attested</span>
                        </div>
                        <p className="text-[11px] text-slate-300">{comp.notes}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing Information Notice */}
              {careerProfile.missing_or_uncertain_information.length > 0 && (
                <div className="mt-6 rounded-xl border border-amber-900/40 bg-amber-950/20 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Identified Information & Evidence Gaps</span>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {careerProfile.missing_or_uncertain_information.map((item: any, i: number) => (
                      <div key={i} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className="text-amber-400">&bull;</span>
                        <div>
                          <strong className="text-white">{item.category}:</strong> {item.detail}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: RECOMMENDED JOB ROLES                                       */}
      {/* =================================================================== */}
      {activeTab === 'roles' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold text-white">Recommended Engineering Roles</h3>
              <p className="text-xs text-slate-400">
                Deterministic archetype fit based on candidate demonstrated skills and project backgrounds.
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-400">Filter:</span>
              {['all', 'Strong Fit', 'Potential Fit', 'Growth Fit'].map((f) => (
                <button
                  key={f}
                  onClick={() => setSelectedRoleFilter(f)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                    selectedRoleFilter === f
                      ? 'bg-indigo-600 text-white'
                      : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white'
                  }`}
                >
                  {f === 'all' ? 'All Roles' : f}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {filteredRoles.map((role: any) => (
              <Card key={role.role_id} className="p-5 border-slate-800 bg-[#0F172A]/90 space-y-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{role.category}</span>
                      <h4 className="text-base font-black text-white">{role.title}</h4>
                    </div>
                    <div className="text-right">
                      <Badge
                        variant={role.fit_tier === 'Strong Fit' ? 'emerald' : (role.fit_tier === 'Potential Fit' ? 'amber' : 'slate')}
                        size="sm"
                      >
                        {role.fit_tier} ({role.match_score}%)
                      </Badge>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-slate-300 leading-relaxed">
                    {role.description}
                  </p>

                  <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/60 p-2.5">
                    <span className="text-[11px] text-slate-400 font-bold block mb-1">Evidence-Grounded Rationale:</span>
                    <p className="text-xs text-slate-200">{role.fit_reason}</p>
                  </div>

                  {/* Matching Skills */}
                  {role.matching_skills.length > 0 && (
                    <div className="mt-3">
                      <span className="text-[11px] text-emerald-400 font-bold block mb-1.5">Matching Competencies:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {role.matching_skills.map((s: string, sIdx: number) => (
                          <span key={sIdx} className="rounded-md border border-emerald-900/40 bg-emerald-950/30 px-2 py-0.5 text-[11px] text-emerald-300">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Gaps */}
                  {role.primary_gaps.length > 0 && (
                    <div className="mt-3">
                      <span className="text-[11px] text-amber-400 font-bold block mb-1.5">Primary Gaps to Close:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {role.primary_gaps.map((g: string, gIdx: number) => (
                          <span key={gIdx} className="rounded-md border border-amber-900/40 bg-amber-950/30 px-2 py-0.5 text-[11px] text-amber-300">
                            {g}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80">
                  <div className="text-[11px] text-slate-400 font-bold">Practical Next Action:</div>
                  <p className="text-xs text-indigo-300 mt-0.5">{role.practical_next_action}</p>
                </div>
              </Card>
            ))}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] text-slate-400">
            <strong>Methodology Transparency:</strong> Recommendations are heuristic competency alignments computed from candidate resume evidence against ResumeMatch AI engineering archetype standards. Real-time market demand and salaries vary by geography and organization.
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: SKILL-GAP INTELLIGENCE                                      */}
      {/* =================================================================== */}
      {activeTab === 'gaps' && (
        <Card className="p-6 border-slate-800 bg-[#0F172A]/90 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-bold text-white">
                Prioritized Skill-Gap Intelligence
              </h3>
              <p className="text-xs text-slate-400">
                Categorized across 4 core engineering domains with 9-point counseling answers.
              </p>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap gap-1.5">
              {[
                { id: 'all', label: 'All Gaps' },
                { id: 'Core Technical Skills', label: 'Core Technical' },
                { id: 'Engineering Tools and Practices', label: 'Engineering Tools' },
                { id: 'Professional and Behavioral Competencies', label: 'Professional & Soft' },
                { id: 'Productivity and Business Tools', label: 'Productivity & BI' }
              ].map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCategory(c.id)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                    selectedCategory === c.id
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white'
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {filteredGaps.map((gap: any, idx: number) => {
              const isCounselingOpen = !!expandedCounseling[gap.skill_name];
              const counseling = gap.counseling_profile || {};

              return (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 transition space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-500/10 text-xs font-bold text-indigo-400 border border-indigo-500/20">
                        {idx + 1}
                      </span>
                      <h4 className="text-sm font-bold text-white">{gap.skill_name}</h4>
                      <Badge variant="indigo" size="sm">{gap.category}</Badge>
                      <Badge variant={gap.priority_tier === 'Mandatory' ? 'rose' : 'amber'} size="sm">
                        {gap.priority_tier}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-400">{gap.priority} ({gap.priority_score} pts)</span>
                      <button
                        onClick={() => toggleCounseling(gap.skill_name)}
                        className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white"
                      >
                        <span>Counseling Profile</span>
                        {isCounselingOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300">{gap.priority_reason}</p>

                  <div className="grid grid-cols-1 gap-2 text-xs md:grid-cols-2">
                    <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-2.5">
                      <span className="text-[11px] text-slate-400 font-bold block mb-1">Supporting Job Description Citation:</span>
                      <p className="text-slate-300 italic">{gap.jd_sentence}</p>
                    </div>

                    <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-2.5">
                      <span className="text-[11px] text-slate-400 font-bold block mb-1">Candidate Foundation / Related Background:</span>
                      <p className="text-slate-300">{gap.related_experience}</p>
                    </div>
                  </div>

                  {/* Expandable 9-Point Counseling Profile */}
                  {isCounselingOpen && (
                    <div className="mt-3 rounded-xl border border-indigo-900/40 bg-indigo-950/20 p-4 space-y-3">
                      <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs border-b border-indigo-900/40 pb-2">
                        <BookOpen className="h-4 w-4" />
                        <span>Professional Counseling Assessment (9-Point Strategic Guide)</span>
                      </div>

                      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 text-xs">
                        <div>
                          <strong className="text-indigo-300 block mb-0.5">1. Why It Matters for Target Position:</strong>
                          <p className="text-slate-300">{counseling.why_it_matters || 'Core technical foundation for scalable development.'}</p>
                        </div>
                        <div>
                          <strong className="text-indigo-300 block mb-0.5">2. Practical Portfolio Deliverable:</strong>
                          <p className="text-emerald-400 font-semibold">{counseling.practical_deliverable || gap.practical_deliverable}</p>
                        </div>
                        <div>
                          <strong className="text-indigo-300 block mb-0.5">3. Verification Criteria:</strong>
                          <p className="text-slate-300">{counseling.verification_method || 'Unit test suite passes and documentation compiles.'}</p>
                        </div>
                        <div>
                          <strong className="text-indigo-300 block mb-0.5">4. Interview Talking Point:</strong>
                          <p className="text-slate-300">{counseling.interview_talking_point || 'Discuss architectural trade-offs and error handling patterns.'}</p>
                        </div>
                      </div>

                      {counseling.post_completion_resume_bullet && (
                        <div className="mt-2 rounded-lg border border-emerald-900/30 bg-emerald-950/30 p-2.5 text-xs">
                          <strong className="text-emerald-400 block mb-1">Post-Completion Resume Bullet Example:</strong>
                          <p className="text-slate-200 font-mono text-[11px]">{counseling.post_completion_resume_bullet}</p>
                          <span className="text-[10px] text-slate-400 mt-1 block italic">*Add only after verifiable implementation artifact is built and pushed to repository.</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* =================================================================== */}
      {/* TAB 4: LEARNING ROADMAPS & STUDY PLAN                              */}
      {/* =================================================================== */}
      {activeTab === 'roadmaps' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold text-white">Step-by-Step Learning Roadmaps</h3>
              <p className="text-xs text-slate-400">7-stage structured curricula with concrete milestones and time commitments.</p>
            </div>
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
                <div key={idx} className="overflow-hidden rounded-xl border border-slate-800 bg-[#0F172A]/80 shadow-md">
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
                          <div key={mIdx} className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
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

          {/* Study Plan Section */}
          {dossier.study_plan && (
            <Card className="p-6 border-slate-800 bg-[#0F172A]/90 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-indigo-400" />
                  <h4 className="text-sm font-bold text-white">
                    {dossier.study_plan.timeline_days}-Day Balanced Study Schedule
                  </h4>
                </div>
                <Badge variant="indigo" size="sm">
                  {dossier.study_plan.daily_hours} hrs/day target
                </Badge>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {(dossier.study_plan.schedule_items || []).slice(0, 14).map((item: any, i: number) => (
                  <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs space-y-1">
                    <div className="flex items-center justify-between text-indigo-300 font-bold">
                      <span>Day {item.day_number}</span>
                      <span className="text-[10px] text-slate-400">~{item.estimated_hours}h</span>
                    </div>
                    <div className="font-semibold text-white text-[11px]">{item.skill_name}</div>
                    <p className="text-slate-400 text-[11px] line-clamp-2">{item.task_description}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 5: ACTIONABLE RECOMMENDATIONS & RESUME ADVISOR                  */}
      {/* =================================================================== */}
      {activeTab === 'recommendations' && (
        <div className="space-y-6">
          {/* Resume Improvement Suggestions */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-bold text-white">Actionable Resume Improvements</h3>
              <p className="text-xs text-slate-400">
                Data-driven recommendations to strengthen recruiter screening conversion and technical credibility.
              </p>
            </div>

            <div className="space-y-3">
              {resumeSuggestions.map((sug: any) => (
                <Card key={sug.suggestion_id} className="p-5 border-slate-800 bg-[#0F172A]/90 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-indigo-400" />
                      <h4 className="text-sm font-bold text-white">{sug.category}</h4>
                    </div>
                    <Badge variant={sug.priority === 'High' ? 'rose' : 'amber'} size="sm">
                      {sug.priority} Priority
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{sug.reason}</p>

                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs space-y-2">
                    <div className="text-[11px] text-slate-400">
                      <strong>Current Evidence Gap:</strong> {sug.evidence_context}
                    </div>

                    <div className="grid grid-cols-1 gap-2 md:grid-cols-2 pt-1 border-t border-slate-800">
                      <div className="rounded bg-rose-950/20 border border-rose-900/30 p-2 text-rose-300 text-[11px]">
                        <strong>Before:</strong> {sug.actionable_example?.before}
                      </div>
                      <div className="rounded bg-emerald-950/20 border border-emerald-900/30 p-2 text-emerald-300 text-[11px]">
                        <strong>After:</strong> {sug.actionable_example?.after}
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-emerald-400 flex items-center gap-1.5">
                    <ArrowRight className="h-3.5 w-3.5" />
                    <span><strong>Action:</strong> {sug.practical_next_action}</span>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Structured Career Roadmap (Short-term & Medium-term) */}
          {careerRoadmap && (
            <Card className="p-6 border-slate-800 bg-[#0F172A]/90 space-y-6">
              <div>
                <h3 className="text-base font-bold text-white">Structured Career Progression Roadmap</h3>
                <p className="text-xs text-slate-400">
                  Targeted milestones for {careerRoadmap.target_role}: bridging short-term skill closing and medium-term cloud authority.
                </p>
              </div>

              {/* Short-Term Milestones */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                  <Clock className="h-4 w-4" />
                  <span>Phase 1: Short-Term Portfolio Deliverables (Weeks 1–8)</span>
                </div>
                <div className="space-y-2.5">
                  {(careerRoadmap.short_term || []).map((m: any) => (
                    <div key={m.milestone_id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{m.title}</span>
                        <Badge variant="indigo" size="sm">{m.timeframe}</Badge>
                      </div>
                      <p className="text-slate-300">{m.goal}</p>
                      <div className="rounded bg-slate-950/60 p-2.5 space-y-1 text-[11px]">
                        <div className="text-slate-400"><strong>Rationale:</strong> {m.reason}</div>
                        <div className="text-emerald-400"><strong>Deliverable:</strong> {m.deliverable}</div>
                        <div className="text-slate-400"><strong>Verification:</strong> {m.verification_criteria}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Medium-Term Milestones */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase tracking-wider">
                  <TrendingUp className="h-4 w-4" />
                  <span>Phase 2: Medium-Term Cloud Deployment & Authority (Months 3–6)</span>
                </div>
                <div className="space-y-2.5">
                  {(careerRoadmap.medium_term || []).map((m: any) => (
                    <div key={m.milestone_id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{m.title}</span>
                        <Badge variant="purple" size="sm">{m.timeframe}</Badge>
                      </div>
                      <p className="text-slate-300">{m.goal}</p>
                      <div className="rounded bg-slate-950/60 p-2.5 space-y-1 text-[11px]">
                        <div className="text-slate-400"><strong>Rationale:</strong> {m.reason}</div>
                        <div className="text-emerald-400"><strong>Deliverable:</strong> {m.deliverable}</div>
                        <div className="text-slate-400"><strong>Verification:</strong> {m.verification_criteria}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
