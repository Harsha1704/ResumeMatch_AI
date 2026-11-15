import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Timer,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Award,
  AlertCircle,
  HelpCircle,
  Loader2,
  Send
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { api } from '../services/api';
import type { HeuristicEvaluation } from '../types';

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
        expected_key_points: q.expected_key_points,
        important_concepts: q.important_concepts,
        framework_id: q.recommended_answer_framework || 'STAR',
        topic: q.topic,
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

  const q = sessionData?.question;
  const currentNum = (sessionData?.current_index ?? 0) + 1;
  const totalNum = sessionData?.total_questions ?? 1;
  const progressPct = Math.round((currentNum / totalNum) * 100);

  const wordCount = userAnswer.trim() ? userAnswer.trim().split(/\s+/).length : 0;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between">
        <Link
          to="/interview-studio"
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Studio</span>
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
            Finish Session
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <Card className="border-slate-800 bg-[#0F172A]/80 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
          <span className="font-bold text-white">
            Question {currentNum} of {totalNum}
          </span>
          <span>{progressPct}% Completed</span>
        </div>
        <ProgressBar percentage={progressPct} color="indigo" />
      </Card>

      {/* Question Card */}
      {q && (
        <Card className="border-slate-800 bg-[#0F172A]/90 p-6 space-y-4">
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

          <h3 className="text-xl font-bold text-white leading-relaxed">
            {q.question_text}
          </h3>

          {/* Key Concepts Checklist */}
          {q.expected_key_points && q.expected_key_points.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                Expected Concepts to Address:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {q.expected_key_points.map((kp: string, idx: number) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300"
                  >
                    <CheckCircle2 className="h-3 w-3 text-indigo-400" />
                    {kp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Answer Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <label className="font-bold text-slate-200 uppercase tracking-wider">
                Your Practice Response:
              </label>
              <span>{wordCount} words &bull; {userAnswer.length} chars</span>
            </div>

            <textarea
              rows={8}
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder={`Draft your verbal answer directly using the ${q.recommended_answer_framework || 'STAR'} methodology...`}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Evaluation Action */}
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
                  <span>Evaluating answer...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Instant Heuristic Evaluation</span>
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
                  <span>Next Question</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleNavigate('finish')}
                  className="flex items-center gap-1 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-600/30 hover:bg-emerald-500"
                >
                  <span>Complete Session</span>
                  <CheckCircle2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Instant Evaluation Results Card */}
          {evaluation && (
            <div className="mt-4 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2">
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  {evaluation.evaluator_label || 'Heuristic Feedback'}
                </span>
                <span className={`text-sm font-black ${evaluation.score >= 70 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  Score: {evaluation.score}/100
                </span>
              </div>

              {evaluation.framework_adherence && (
                <div className="text-xs text-slate-300">
                  <span className="font-semibold text-slate-400">Framework Sections Addressed:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {evaluation.framework_adherence.sections_addressed?.map((s, i) => (
                      <Badge key={i} variant="emerald" size="sm">{s}</Badge>
                    ))}
                    {evaluation.framework_adherence.missing_sections?.map((s, i) => (
                      <Badge key={i} variant="rose" size="sm">Missing: {s}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {evaluation.feedback_notes && evaluation.feedback_notes.length > 0 && (
                <div className="text-xs text-slate-400 space-y-1">
                  <span className="font-semibold text-slate-300">Coaching Notes:</span>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {evaluation.feedback_notes.map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
