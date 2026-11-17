import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Timer,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  HelpCircle,
  Loader2,
  BookOpen,
  ShieldAlert
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { api } from '../services/api';
import type { HeuristicEvaluation, InterviewQuestion } from '../types';

export const InterviewPracticePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id') || undefined;
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [sessionData, setSessionData] = useState<any>(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Instant evaluation state
  const [evaluating, setEvaluating] = useState(false);
  const [evaluation, setEvaluation] = useState<HeuristicEvaluation | null>(null);

  // Framework guidance toggle
  const [showGuidance, setShowGuidance] = useState(false);

  // Timer effect
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const fetchCurrentQuestion = async (sid?: string) => {
    setLoading(true);
    setEvaluation(null);
    try {
      const res = await api.getInterviewPractice(sid);
      setSessionData(res);
      setUserAnswer(res.question?.user_answer || '');
      if (res.question?.evaluation) {
        setEvaluation(res.question.evaluation);
      }
    } catch (err) {
      console.warn('Practice fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentQuestion(sessionId);
  }, [sessionId]);

  const handleEvaluateInstant = async () => {
    if (!userAnswer.trim() || !sessionData?.question) return;
    setEvaluating(true);
    try {
      const q = sessionData.question;
      const res = await api.evaluateAnswer({
        user_answer: userAnswer,
        question_text: q.question_text,
        expected_key_points: q.expected_key_points || q.expected_answer_evaluation_criteria,
        important_concepts: q.important_concepts,
        framework_id: q.recommended_answer_framework || 'STAR',
        topic: q.topic || q.related_skill,
      });
      setEvaluation(res);
    } catch (err) {
      console.error(err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleNavigate = async (direction: 'next' | 'prev' | 'finish') => {
    if (!sessionData?.session_id) return;
    setLoading(true);
    try {
      const res = await api.submitPracticeAnswer(
        sessionData.session_id,
        sessionData.current_index || 0,
        userAnswer,
        direction
      );
      if (direction === 'finish' || res.is_finished) {
        navigate(`/interview-results?session_id=${encodeURIComponent(sessionData.session_id)}`);
      } else {
        await fetchCurrentQuestion(sessionData.session_id);
      }
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  if (loading && !sessionData) {
    return <LoadingSpinner message="Initializing practice session..." />;
  }

  const q: InterviewQuestion | undefined = sessionData?.question;
  const currentNum = (sessionData?.current_index ?? 0) + 1;
  const totalNum = sessionData?.total_questions ?? 1;
  const progressPct = Math.round((currentNum / totalNum) * 100);

  const wordCount = userAnswer.trim() ? userAnswer.trim().split(/\s+/).length : 0;
  const charCount = userAnswer.length;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between">
        <Link
          to="/interview-studio"
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Exit to Studio</span>
        </Link>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-bold text-indigo-400">
            <Timer className="h-3.5 w-3.5" />
            <span>{formatTimer(elapsedSeconds)}</span>
          </div>
          <button
            onClick={() => handleNavigate('finish')}
            className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20"
          >
            Finish &amp; View Summary
          </button>
        </div>
      </div>

      {/* Progress Bar Card */}
      <Card className="border-slate-800 bg-[#0F172A]/80 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
          <span>
            Question <strong className="text-white">{currentNum}</strong> of{' '}
            <strong className="text-white">{totalNum}</strong>
          </span>
          <span className="font-semibold text-indigo-400">{progressPct}% Complete</span>
        </div>
        <ProgressBar percentage={progressPct} color="indigo" />
      </Card>

      {/* Active Question Card */}
      {q && (
        <Card className="border-slate-800 bg-[#0F172A]/80 p-6 space-y-4">
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
                <span className="rounded bg-indigo-950 border border-indigo-700/60 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                  Skill: {q.related_skill}
                </span>
              )}
              <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                Framework: {q.recommended_answer_framework || 'STAR'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowGuidance(!showGuidance)}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>{showGuidance ? 'Hide Framework Hint' : 'Show Framework Hint'}</span>
            </button>
          </div>

          {/* Question Text */}
          <h3 className="text-lg font-bold text-white leading-snug">
            {currentNum}. {q.question_text}
          </h3>

          {/* Reason for Asking */}
          {q.reason_for_asking && (
            <div className="flex items-start gap-2.5 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs text-slate-300">
              <HelpCircle className="h-4 w-4 shrink-0 text-indigo-400 mt-0.5" />
              <div>
                <strong className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider block">
                  Why the Interviewer Asks This:
                </strong>
                <p className="mt-0.5 text-slate-300">{q.reason_for_asking}</p>
              </div>
            </div>
          )}

          {/* Expected Evaluation Criteria */}
          {q.expected_answer_evaluation_criteria && q.expected_answer_evaluation_criteria.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Evaluation Criteria (What a strong answer demonstrates):
              </span>
              <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc">
                {q.expected_answer_evaluation_criteria.map((crit, idx) => (
                  <li key={idx}>{crit}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Framework Guidance Accordion */}
          {showGuidance && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2 text-xs text-slate-300">
              <span className="font-bold text-amber-300 uppercase tracking-wider block text-[10px]">
                Recommended Structure ({q.recommended_answer_framework || 'STAR'} Methodology)
              </span>
              <p className="text-slate-400">
                Structure your response with clear sections: state the engineering context (Situation/Task), your specific technical implementation (Action), and verified quantitative impact (Result).
              </p>
            </div>
          )}

          {/* Answer Input Area */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Your Written Answer
              </label>
              <div className="flex items-center gap-3 text-[11px] text-slate-500">
                <span>{charCount} characters</span>
                <span className={wordCount >= 60 ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
                  {wordCount} words (aim for 60-150)
                </span>
              </div>
            </div>

            <textarea
              rows={8}
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder={`Write your answer here. Use the ${q.recommended_answer_framework || 'STAR'} framework (Situation, Task, Action, Result) with specific tools, metrics, and genuine project experience...`}
              className="w-full rounded-xl border border-slate-700 bg-slate-900/90 p-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed font-sans"
            />
          </div>

          {/* Evaluation Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={handleEvaluateInstant}
              disabled={evaluating || !userAnswer.trim()}
              className="flex items-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {evaluating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Evaluating Answer...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Evaluate Answer Draft</span>
                </>
              )}
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleNavigate('prev')}
                disabled={currentNum <= 1}
                className="flex items-center gap-1 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous</span>
              </button>

              {currentNum < totalNum ? (
                <button
                  type="button"
                  onClick={() => handleNavigate('next')}
                  className="flex items-center gap-1 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
                >
                  <span>Submit &amp; Next</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleNavigate('finish')}
                  className="flex items-center gap-1 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-600/30 hover:bg-emerald-500"
                >
                  <span>Submit &amp; Finish</span>
                  <CheckCircle2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Instant Detailed Heuristic Feedback Drawer */}
          {evaluation && (
            <div className="mt-6 rounded-2xl border border-indigo-500/30 bg-[#0B1120] p-5 space-y-4 shadow-xl">
              <div className="flex flex-wrap items-center justify-between border-b border-indigo-500/20 pb-3 gap-2">
                <div>
                  <span className="text-xs font-bold text-white uppercase tracking-wider block">
                    {evaluation.evaluator_label || 'Heuristic Answer Feedback'}
                  </span>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Deterministic coaching analysis across 6 criteria.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Overall Score:</span>
                  <span className={`text-base font-black ${
                    (evaluation.overall_score || evaluation.score || 0) >= 70
                      ? 'text-emerald-400'
                      : (evaluation.overall_score || evaluation.score || 0) >= 50
                      ? 'text-amber-400'
                      : 'text-rose-400'
                  }`}>
                    {evaluation.overall_score ?? evaluation.score ?? 0} / 100
                  </span>
                </div>
              </div>

              {/* Evidence Grounding Warnings Banner */}
              {evaluation.evidence_grounding_warnings && evaluation.evidence_grounding_warnings.length > 0 && (
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
                    <ShieldAlert className="h-4 w-4 text-amber-400" />
                    <span>Evidence-Grounding Warning</span>
                  </div>
                  <ul className="text-xs text-amber-200/90 pl-5 list-disc space-y-0.5">
                    {evaluation.evidence_grounding_warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 6 Individual Criterion Scores Breakdown */}
              {evaluation.criterion_scores && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Individual Criterion Breakdown
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {Object.entries(evaluation.criterion_scores).map(([critKey, critData]: [string, any]) => (
                      <div
                        key={critKey}
                        className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-200 capitalize">
                            {critKey.replace('_', ' ')}
                          </span>
                          <div className="flex items-center gap-1.5">
                            {critData.status && (
                              <span className={`text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded border ${
                                critData.status === 'verified' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                critData.status === 'recognized' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                                critData.status === 'warning' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                'bg-slate-800 text-slate-400 border-slate-700'
                              }`}>
                                {critData.status}
                              </span>
                            )}
                            <span className={`font-bold ${critData.score >= 70 ? 'text-emerald-400' : 'text-amber-400'}`}>
                              {critData.score}%
                            </span>
                          </div>
                        </div>
                        <ProgressBar percentage={critData.score} color={critData.score >= 70 ? 'emerald' : 'amber'} />
                        <p className="text-[10px] text-slate-400 line-clamp-2 mt-1">
                          {critData.details}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Strengths & Missing Concepts Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                {evaluation.strengths && evaluation.strengths.length > 0 && (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5 space-y-1.5">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">
                      Observed Strengths
                    </span>
                    <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc">
                      {evaluation.strengths.map((str, i) => (
                        <li key={i}>{str}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(evaluation.missing_concepts || evaluation.areas_for_improvement) && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5 space-y-1.5">
                    <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block">
                      Improvement Suggestions &amp; Missing Concepts
                    </span>
                    <ul className="text-xs text-slate-300 space-y-1 pl-4 list-disc">
                      {(evaluation.improvement_suggestions || evaluation.areas_for_improvement || []).map((imp, i) => (
                        <li key={i}>{imp}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Suggested Improved Answer Structure Guide */}
              {evaluation.suggested_improved_answer_structure && (
                <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/30 p-4 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-300">
                    <BookOpen className="h-4 w-4 text-indigo-400" />
                    <span>
                      Suggested Answer Structure Guide ({evaluation.suggested_improved_answer_structure.framework_name})
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {evaluation.suggested_improved_answer_structure.recommended_steps?.map((stepItem, i) => (
                      <div key={i} className="text-xs text-slate-300">
                        <strong className="text-indigo-400">{stepItem.step}:</strong> {stepItem.guidance}
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-500 pt-1 italic">
                    {evaluation.suggested_improved_answer_structure.safeguard_note}
                  </p>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-[10px] text-slate-500 italic pt-1 border-t border-slate-800/80">
                {evaluation.disclaimer || 'Feedback is automated, rule-based, and heuristic for self-guided practice.'}
              </p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
