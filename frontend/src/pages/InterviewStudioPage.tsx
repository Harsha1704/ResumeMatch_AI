import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Sliders,
  PlayCircle,
  Copy,
  Check,
  ShieldCheck,
  BookOpen,
  History,
  Trash2,
  HelpCircle,
  Clock
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';
import type { InterviewQuestion, InterviewEvidence, InterviewSessionItem } from '../types';

export const InterviewStudioPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentAnalysis } = useAnalysis();

  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState<InterviewEvidence | null>(null);
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [technicalTopics, setTechnicalTopics] = useState<string[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Practice History state
  const [historySessions, setHistorySessions] = useState<InterviewSessionItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<'questions' | 'history'>('questions');

  // Form controls
  const [category, setCategory] = useState('ALL');
  const [difficulty, setDifficulty] = useState('All');
  const [interviewMode, setInterviewMode] = useState('mixed');
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
        maxQuestions,
        interviewMode,
        evidence?.job_title
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

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.getInterviewSessions(currentAnalysis?.analysis_id);
      setHistorySessions(res.sessions || []);
    } catch (err) {
      console.warn('Error fetching session history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
    fetchHistory();
  }, [currentAnalysis?.analysis_id]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.generateInterviewQuestions({
        id: currentAnalysis?.analysis_id,
        category,
        difficulty,
        mode: interviewMode,
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
        mode: interviewMode,
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

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await api.deleteInterviewSession(sessionId);
      setHistorySessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
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
              <Badge variant="indigo" size="sm">INTERVIEW STUDIO</Badge>
              <Badge variant="emerald" size="sm">ZERO LLM / DETERMINISTIC</Badge>
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
              Interview Intelligence Studio
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Role-specific question generation, evidence-grounded answer evaluation, and practice progress tracking.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {activeSessionId && (
              <Link
                to={`/interview-practice?session_id=${encodeURIComponent(activeSessionId)}`}
                className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-amber-500/20 hover:bg-amber-400"
              >
                <PlayCircle className="h-4 w-4" />
                <span>Resume Practice</span>
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
                Active Candidate Resume
              </span>
              <p className="mt-1 text-xs font-bold text-white truncate" title={evidence.filename}>
                {evidence.filename || 'Candidate Resume'}
              </p>
              <span className="text-[10px] text-emerald-400">Verified Evidence</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Target Role
              </span>
              <p className="mt-1 text-xs font-bold text-indigo-300 truncate" title={evidence.job_title}>
                {evidence.job_title || 'Software Engineer'}
              </p>
              <span className="text-[10px] text-slate-400">Evaluated Position</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Projects
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.projects_count ?? 1}
              </span>
              <span className="text-[10px] text-slate-400">Extracted Projects</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Internships
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.internships_count ?? 1}
              </span>
              <span className="text-[10px] text-slate-400">Practical Experience</span>
            </div>

            <div className="px-3 pt-3 sm:pt-0 text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Resume Skills
              </span>
              <span className="mt-1 block text-lg font-black text-white">
                {evidence.total_skills ?? 7}
              </span>
              <span className="text-[10px] text-slate-400">Demonstrated Skills</span>
            </div>
          </div>
        </Card>
      )}

      {/* Navigation Tabs: Questions vs Practice History */}
      <div className="flex border-b border-slate-800 space-x-4">
        <button
          onClick={() => setActiveTab('questions')}
          className={`flex items-center gap-2 pb-3 text-xs font-bold transition border-b-2 ${
            activeTab === 'questions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="h-4 w-4" />
          <span>Question Bank &amp; Complete Answers ({questions.length})</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('history');
            fetchHistory();
          }}
          className={`flex items-center gap-2 pb-3 text-xs font-bold transition border-b-2 ${
            activeTab === 'history'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="h-4 w-4" />
          <span>Practice History ({historySessions.length})</span>
        </button>
      </div>

      {activeTab === 'questions' ? (
        <>
          {/* Question Generation Controls Form */}
          <Card
            title="Interview Customization &amp; Question Generation"
            subtitle="Configure interview mode, difficulty level, and focus area"
            icon={Sliders}
          >
            <form onSubmit={handleGenerate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6 items-end">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Interview Mode
                </label>
                <select
                  value={interviewMode}
                  onChange={(e) => setInterviewMode(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
                >
                  <option value="mixed">Mixed (All Modes)</option>
                  <option value="technical">Technical Deep-Dive</option>
                  <option value="behavioral">Behavioral &amp; Projects</option>
                  <option value="hr">HR &amp; Soft Skills</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
                >
                  <option value="All">All Levels (Balanced)</option>
                  <option value="Beginner">Beginner / Easy</option>
                  <option value="Intermediate">Intermediate / Medium</option>
                  <option value="Advanced">Advanced / Hard</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
                >
                  <option value="ALL">All Categories</option>
                  <option value="A">Resume Skills</option>
                  <option value="B">Project Deep-Dive</option>
                  <option value="C">Internships</option>
                  <option value="D">Job Gaps &amp; Alignment</option>
                  <option value="E">Technical Bank</option>
                  <option value="F">HR / Behavioral</option>
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
                  Technical Topic
                </label>
                <select
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:outline-none"
                >
                  <option value="All">All Domains</option>
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
                  Update Question Bank
                </button>
              </div>
            </form>
          </Card>

          {/* Questions Portfolio List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">
                Generated Practice Questions ({questions.length})
              </h3>
              <span className="text-xs text-slate-400">
                Grounding: 100% extracted resume artifacts and verified question bank
              </span>
            </div>

            {questions.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-[#0F172A]/60 p-12 text-center text-xs text-slate-400">
                No questions found for the selected criteria. Adjust filters and click Update Question Bank.
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
                        {q.related_skill && (
                          <span className="rounded bg-indigo-950/80 border border-indigo-700/50 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                            Skill: {q.related_skill}
                          </span>
                        )}
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

                    {/* Reason for Asking */}
                    {q.reason_for_asking && (
                      <div className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs text-slate-300">
                        <HelpCircle className="h-4 w-4 shrink-0 text-indigo-400 mt-0.5" />
                        <div>
                          <strong className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider block">
                            Reason for Asking:
                          </strong>
                          <p className="mt-0.5">{q.reason_for_asking}</p>
                        </div>
                      </div>
                    )}

                    {/* Expected Evaluation Criteria */}
                    {q.expected_answer_evaluation_criteria && q.expected_answer_evaluation_criteria.length > 0 && (
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                          Expected Answer Evaluation Criteria:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {q.expected_answer_evaluation_criteria.map((kp: string, i: number) => (
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
                            Model Answer:
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
                              Detailed Answer
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
        </>
      ) : (
        /* Practice History Tab */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-white">
                Practice Session History
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Saved sessions, answers, and deterministic heuristic evaluation results.
              </p>
            </div>
            <button
              onClick={fetchHistory}
              disabled={loadingHistory}
              className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              Refresh
            </button>
          </div>

          {loadingHistory ? (
            <LoadingSpinner message="Loading your practice history..." />
          ) : historySessions.length === 0 ? (
            <Card className="border-slate-800 bg-[#0F172A]/60 p-12 text-center">
              <History className="h-8 w-8 text-slate-500 mx-auto mb-3" />
              <h4 className="text-sm font-bold text-white">No practice sessions found</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                You have not started any interview practice sessions yet. Click "Start Practice Session" above to begin practicing.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {historySessions.map((sessionItem) => (
                <div
                  key={sessionItem.session_id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-800 bg-[#0F172A]/80 p-5 shadow-lg gap-4 hover:border-slate-700 transition"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-white">
                        {sessionItem.target_role || sessionItem.job_title || 'Software Engineer'}
                      </span>
                      <Badge
                        variant={sessionItem.is_completed ? 'emerald' : 'amber'}
                        size="sm"
                      >
                        {sessionItem.is_completed ? 'COMPLETED' : 'IN PROGRESS'}
                      </Badge>
                      <Badge variant="indigo" size="sm">
                        Mode: {sessionItem.interview_mode || 'mixed'}
                      </Badge>
                      <Badge variant="slate" size="sm">
                        Difficulty: {sessionItem.difficulty || 'all'}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-slate-500" />
                        {new Date(sessionItem.created_at * 1000).toLocaleDateString()} at{' '}
                        {new Date(sessionItem.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span>
                        Questions: <strong className="text-slate-200">{sessionItem.answered_questions} / {sessionItem.total_questions}</strong>
                      </span>
                      {sessionItem.results_summary?.overall_score !== undefined && (
                        <span>
                          Score: <strong className="text-emerald-400">{sessionItem.results_summary.overall_score}%</strong>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {sessionItem.is_completed ? (
                      <Link
                        to={`/interview-results?session_id=${encodeURIComponent(sessionItem.session_id)}`}
                        className="rounded-xl bg-slate-800 border border-slate-700 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
                      >
                        View Results
                      </Link>
                    ) : (
                      <Link
                        to={`/interview-practice?session_id=${encodeURIComponent(sessionItem.session_id)}`}
                        className="rounded-xl bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
                      >
                        Resume Practice
                      </Link>
                    )}
                    <button
                      onClick={() => handleDeleteSession(sessionItem.session_id)}
                      className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-2 text-rose-300 hover:bg-rose-500/20"
                      title="Safely Delete Session"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
