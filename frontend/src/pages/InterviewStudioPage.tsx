import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Sparkles,
  Sliders,
  PlayCircle,
  Copy,
  Check,
  FileText,
  Briefcase,
  GraduationCap,
  Layers,
  ShieldCheck,
  Code2,
  ChevronRight,
  BookOpen,
  CheckCircle2
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { InterviewQuestion, InterviewEvidence } from '../types';

export const InterviewStudioPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentAnalysis } = useAnalysis();

  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState<InterviewEvidence | null>(null);
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [technicalTopics, setTechnicalTopics] = useState<string[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Form controls
  const [category, setCategory] = useState('ALL');
  const [difficulty, setDifficulty] = useState('All');
  const [maxQuestions, setMaxQuestions] = useState(10);
  const [topic, setTopic] = useState('All');

  // Toggle mode for answers: detailed vs simpler
  const [answerModes, setAnswerModes] = useState<Record<string, 'detailed' | 'simpler'>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const res = await api.getInterviewStudio(
        currentAnalysis?.analysis_id,
        category,
        difficulty,
        maxQuestions
      );
      setEvidence(res.evidence);
      setQuestions(res.questions || []);
      setTechnicalTopics(res.technical_topics || []);
      if (res.active_session_id) setActiveSessionId(res.active_session_id);
    } catch (err) {
      console.warn('Error fetching interview questions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, [currentAnalysis?.analysis_id]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.generateInterviewQuestions({
        id: currentAnalysis?.analysis_id,
        category,
        difficulty,
        max_questions: maxQuestions,
        technical_topic: topic,
        action: 'generate',
      });
      setEvidence(res.evidence);
      setQuestions(res.questions || []);
      if (res.active_session_id) setActiveSessionId(res.active_session_id);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartPracticeAll = async () => {
    try {
      const res = await api.generateInterviewQuestions({
        id: currentAnalysis?.analysis_id,
        category,
        difficulty,
        max_questions: maxQuestions,
        technical_topic: topic,
        action: 'practice',
      });
      if (res.active_session_id) {
        navigate(`/interview-practice?session_id=${encodeURIComponent(res.active_session_id)}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePracticeSingle = async (questionId: string) => {
    try {
      const res = await api.generateInterviewQuestions({
        id: currentAnalysis?.analysis_id,
        action: 'practice_single',
        question_id: questionId,
      });
      if (res.active_session_id) {
        navigate(`/interview-practice?session_id=${encodeURIComponent(res.active_session_id)}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const toggleAnswerMode = (qId: string, mode: 'detailed' | 'simpler') => {
    setAnswerModes(prev => ({ ...prev, [qId]: mode }));
  };

  const copyAnswer = (qId: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(qId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading && !evidence) {
    return <LoadingSpinner message="Generating deterministic interview question bank..." />;
  }

  return (
    <div className="space-y-6">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-900 p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <Badge variant="indigo" size="sm">MODULE ACTIVE</Badge>
              <Badge variant="emerald" size="sm">ZERO LLM / 100% DETERMINISTIC</Badge>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
              Interview Intelligence Studio
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Resume-aware interview preparation, curated computer science question banks, and complete structured answers.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {activeSessionId && (
              <Link
                to={`/interview-practice?session_id=${encodeURIComponent(activeSessionId)}`}
                className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-amber-500/20 hover:bg-amber-400"
              >
                <PlayCircle className="h-4 w-4" />
                <span>Resume Practice Session</span>
              </Link>
            )}
            <button
              onClick={handleStartPracticeAll}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500"
            >
              <PlayCircle className="h-4 w-4" />
              <span>Start Practice Session</span>
            </button>
          </div>
        </div>
      </div>

      {/* Candidate Profile Context Bar */}
      {evidence && (
        <Card className="border-slate-800 bg-[#0F172A]/80 p-4">
          <div className="grid grid-cols-2 gap-4 divide-y divide-slate-800 sm:grid-cols-5 sm:divide-y-0 sm:divide-x sm:divide-slate-800/80">
            <div className="px-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Active Resume
              </span>
              <p className="mt-1 text-xs font-bold text-white truncate" title={evidence.filename}>
                {evidence.filename || 'Candidate Resume'}
              </p>
              <span className="text-[10px] text-emerald-400">Verified Profile</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Target Job Role
              </span>
              <p className="mt-1 text-xs font-bold text-indigo-300 truncate" title={evidence.job_title}>
                {evidence.job_title || 'Software Engineer'}
              </p>
              <span className="text-[10px] text-slate-400">Target Role</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Projects
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.projects_count ?? 1}
              </span>
              <span className="text-[10px] text-slate-400">Detected Projects</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Internships
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.internships_count ?? 1}
              </span>
              <span className="text-[10px] text-slate-400">Verified Records</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Candidate Skills
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.total_skills ?? 7}
              </span>
              <span className="text-[10px] text-slate-400">Technical Skills</span>
            </div>
          </div>
        </Card>
      )}

      {/* Methodology Transparency Notice */}
      <div className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-xs text-slate-400">
        <ShieldCheck className="h-5 w-5 shrink-0 text-indigo-400" />
        <div>
          <strong className="text-slate-200 uppercase tracking-wide">Methodology Transparency: Deterministic Coaching</strong>
          <p className="mt-0.5 leading-relaxed">
            All interview questions, complete answers, architectural trade-offs, and concept explanations are produced via deterministic NLP and curated expert question banks without generative AI hallucinations. High-level resume matching compatibility scores utilize our trained Supervised ML classifier.
          </p>
        </div>
      </div>

      {/* Question Generation Controls Form */}
      <Card
        title="Question Generation &amp; Complete Answer Controls"
        subtitle="Filter by competency category, difficulty tier, and CS topic"
        icon={Sliders}
      >
        <form onSubmit={handleGenerate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 items-end">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Interview Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="ALL">All Categories (Balanced Mix)</option>
              <option value="A">Category A: Resume Profile &amp; Skills</option>
              <option value="B">Category B: Extracted Projects (Deep-Dive)</option>
              <option value="C">Category C: Internships &amp; Experience</option>
              <option value="D">Category D: Target Job &amp; Skill Gaps</option>
              <option value="E">Category E: Technical Knowledge Bank</option>
              <option value="F">Category F: HR &amp; Behavioral</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Difficulty Level
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="All">All (Balanced Mix)</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Max Questions
            </label>
            <select
              value={maxQuestions}
              onChange={(e) => setMaxQuestions(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value={5}>5 Questions</option>
              <option value={10}>10 Questions</option>
              <option value={15}>15 Questions</option>
              <option value={25}>25 Questions</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Technical Topic (Cat E)
            </label>
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="All">All 18 CS Domains</option>
              {technicalTopics.map((top, idx) => (
                <option key={idx} value={top}>{top}</option>
              ))}
            </select>
          </div>

          <div>
            <button
              type="submit"
              className="w-full rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
            >
              Generate Answers
            </button>
          </div>
        </form>
      </Card>

      {/* Questions Portfolio List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">
            Interview Questions &amp; Complete Answers ({questions.length})
          </h3>
          <span className="text-xs text-slate-400">
            Tailored to verified evidence registry
          </span>
        </div>

        {questions.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-[#0F172A]/60 p-12 text-center text-xs text-slate-400">
            No questions found for the selected criteria. Adjust filters and click Generate Answers.
          </div>
        ) : (
          questions.map((q: any, idx: number) => {
            const mode = answerModes[q.question_id] || 'detailed';
            const isCopied = copiedId === q.question_id;
            return (
              <div
                key={q.question_id || idx}
                className="rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6 shadow-lg space-y-4 hover:border-slate-700 transition"
              >
                {/* Header with badges */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="indigo" size="sm">
                      {q.category_name || q.category}
                    </Badge>
                    <Badge
                      variant={
                        q.difficulty === 'Hard'
                          ? 'rose'
                          : q.difficulty === 'Medium'
                          ? 'amber'
                          : 'emerald'
                      }
                      size="sm"
                    >
                      {q.difficulty}
                    </Badge>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                      Framework: {q.recommended_answer_framework || 'STAR'}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {q.source_reference || 'Resume Evidence'}
                  </span>
                </div>

                {/* Question Text */}
                <h4 className="text-base font-bold text-white leading-snug">
                  {idx + 1}. {q.question_text}
                </h4>

                {/* Key Points to Address */}
                {q.expected_key_points && q.expected_key_points.length > 0 && (
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                      Key Concepts to Address:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {q.expected_key_points.map((kp: string, i: number) => (
                        <span
                          key={i}
                          className="rounded bg-slate-800/90 border border-slate-700/80 px-2 py-0.5 text-[11px] text-slate-300"
                        >
                          &bull; {kp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Complete Answer Container */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-400">
                        Complete Answer:
                      </span>
                      <div className="inline-flex rounded-lg border border-slate-700 bg-slate-800 p-0.5 text-[11px]">
                        <button
                          type="button"
                          onClick={() => toggleAnswerMode(q.question_id, 'detailed')}
                          className={`rounded px-2 py-0.5 font-medium transition ${
                            mode === 'detailed'
                              ? 'bg-indigo-600 text-white'
                              : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          Spoken Answer
                        </button>
                        <button
                          type="button"
                          onClick={() => toggleAnswerMode(q.question_id, 'simpler')}
                          className={`rounded px-2 py-0.5 font-medium transition ${
                            mode === 'simpler'
                              ? 'bg-indigo-600 text-white'
                              : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          Simpler Explanation
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => copyAnswer(q.question_id, mode === 'detailed' ? (q.detailed_answer || q.question_text) : (q.simpler_answer || q.short_answer || q.detailed_answer))}
                        className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300 hover:text-white"
                      >
                        {isCopied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{isCopied ? 'Copied' : 'Copy'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handlePracticeSingle(q.question_id)}
                        className="flex items-center gap-1 rounded bg-indigo-600 px-3 py-1 text-[11px] font-bold text-white hover:bg-indigo-500"
                      >
                        <PlayCircle className="h-3 w-3" />
                        <span>Practice This</span>
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line">
                    {mode === 'detailed'
                      ? q.detailed_answer || 'Complete verbal response crafted for technical interviews.'
                      : q.simpler_answer || q.short_answer || q.detailed_answer}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
