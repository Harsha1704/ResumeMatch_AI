import React, { useRef, useEffect, useState } from 'react';
import {
  Bot,
  User,
  Sparkles,
  HelpCircle,
  Clock,
  Radio,
  Edit3,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  ArrowRight,
  Send,
} from 'lucide-react';
import type { VoiceTranscriptEntry, SpeechRecognitionStatus } from '../../types/voice';

interface LiveTranscriptProps {
  transcript: VoiceTranscriptEntry[];
  currentQuestion: any;
  currentIndex: number;
  totalQuestions: number;
  candidateAnswer: string;
  interimSpeech: string;
  isListening: boolean;
  recognitionStatus: SpeechRecognitionStatus;
  manualMode: boolean;
  onAnswerChange: (newAnswer: string) => void;
  onSubmitAnswer: () => void;
  onRequestFollowup?: () => void;
  hasFollowup?: boolean;
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({
  transcript,
  currentQuestion,
  currentIndex,
  totalQuestions,
  candidateAnswer,
  interimSpeech,
  isListening,
  recognitionStatus,
  manualMode,
  onAnswerChange,
  onSubmitAnswer,
  onRequestFollowup,
  hasFollowup,
}) => {
  const scrollEndRef = useRef<HTMLDivElement | null>(null);
  const [showStarGuide, setShowStarGuide] = useState<boolean>(false);

  // Auto-scroll on new transcript entries or interim speech updates
  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript.length, interimSpeech]);

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getBadgeForType = (type: string) => {
    switch (type) {
      case 'greeting':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Greeting</span>;
      case 'question':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Question</span>;
      case 'feedback':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Feedback</span>;
      case 'followup':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Follow-up</span>;
      case 'closing':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">Closing</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-700 text-slate-300">Answer</span>;
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Prominent Current Question Spotlight Card */}
      {currentQuestion && (
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800/80 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-sm">
                Question {currentIndex + 1}
                {totalQuestions > 0 && <span className="text-slate-400 font-normal"> of {totalQuestions}</span>}
              </span>
              {currentQuestion.category && (
                <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-medium">
                  {currentQuestion.category}
                </span>
              )}
              {currentQuestion.difficulty && (
                <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-[10px] capitalize font-medium">
                  {currentQuestion.difficulty}
                </span>
              )}
            </div>

            <button
              onClick={() => setShowStarGuide(!showStarGuide)}
              className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
              aria-expanded={showStarGuide}
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>{showStarGuide ? 'Hide STAR Tips' : 'STAR Answer Tips'}</span>
              {showStarGuide ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>

          <p className="text-sm font-medium text-slate-100 leading-relaxed">
            {currentQuestion.question_text || currentQuestion.question}
          </p>

          {/* STAR Framework Guidance Accordion */}
          {showStarGuide && (
            <div className="p-3 bg-indigo-950/20 border border-indigo-500/20 rounded-xl text-xs space-y-1.5 text-slate-300 animate-in fade-in duration-200">
              <p className="font-semibold text-indigo-300 text-[11px] uppercase tracking-wider">
                Recommended STAR Framework Response
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
                <div>
                  <strong className="text-slate-200">Situation & Task:</strong> Briefly define the project context, technical challenge, and your responsibility.
                </div>
                <div>
                  <strong className="text-slate-200">Action & Result:</strong> Detail specific technologies, design decisions, and measurable outcomes.
                </div>
              </div>
            </div>
          )}

          {/* Adaptive Follow-up Prompt Banner */}
          {hasFollowup && onRequestFollowup && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between gap-3 text-xs text-amber-200 animate-in fade-in duration-200">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
                <span>The interviewer noted an opportunity for an adaptive follow-up.</span>
              </div>
              <button
                onClick={onRequestFollowup}
                className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-xs transition cursor-pointer shrink-0"
              >
                Hear Follow-up
              </button>
            </div>
          )}
        </div>
      )}

      {/* Transcript Conversation History Area */}
      <div
        className="flex-1 min-h-[300px] max-h-[460px] overflow-y-auto p-4 sm:p-5 bg-slate-900/60 border border-slate-800 rounded-2xl shadow-inner space-y-4"
        role="log"
        aria-live="polite"
        aria-label="Interview Transcript Log"
      >
        {transcript.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[220px] text-center p-6 text-slate-500 space-y-2 select-none">
            <Radio className="w-8 h-8 text-slate-600 animate-pulse" />
            <p className="text-xs font-semibold text-slate-400">Interview Transcript Will Stream Here</p>
            <p className="text-[11px] text-slate-500 max-w-sm">
              The AI interviewer will ask questions aloud, and your spoken answers will be transcribed in real time.
            </p>
          </div>
        ) : (
          transcript.map((entry) => {
            const isInterviewer = entry.speaker === 'interviewer';
            return (
              <div
                key={entry.entry_id}
                className={`flex gap-3 text-xs leading-relaxed animate-in fade-in duration-150 ${
                  isInterviewer ? 'justify-start' : 'justify-end'
                }`}
              >
                {isInterviewer && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-4 space-y-1.5 shadow-sm ${
                    isInterviewer
                      ? 'bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-tl-sm'
                      : 'bg-gradient-to-tr from-indigo-600 to-indigo-700 text-white rounded-tr-sm shadow-indigo-600/20'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3 text-[10px]">
                    <span className="font-semibold flex items-center gap-1.5 opacity-90">
                      {isInterviewer ? 'AI Interviewer' : 'You (Candidate)'}
                      {getBadgeForType(entry.message_type)}
                    </span>
                    <span className="opacity-60 font-mono">{formatTime(entry.timestamp)}</span>
                  </div>

                  <p className="text-xs whitespace-pre-wrap leading-relaxed">{entry.message_text}</p>
                </div>

                {!isInterviewer && (
                  <div className="w-8 h-8 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Live Listening Interim Speech Bubble */}
        {isListening && interimSpeech && (
          <div className="flex justify-end gap-3 text-xs animate-in fade-in duration-150">
            <div className="max-w-[85%] rounded-2xl p-3.5 bg-indigo-950/50 border border-indigo-500/40 text-indigo-200 italic space-y-1 shadow-md">
              <div className="flex items-center gap-2 text-[10px] text-indigo-400 font-semibold not-italic">
                <Radio className="w-3 h-3 animate-ping" />
                <span>Transcribing live candidate speech...</span>
              </div>
              <p className="text-xs">{interimSpeech}</p>
            </div>
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
              <User className="w-4 h-4" />
            </div>
          </div>
        )}

        <div ref={scrollEndRef} />
      </div>

      {/* Candidate Answer Editor Area (Transcribed or Typed) */}
      <div className="p-4 sm:p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-200">
            <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Your Response (Voice-Transcribed or Typed)</span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            {candidateAnswer.trim().split(/\s+/).filter(Boolean).length} words
          </span>
        </div>

        <textarea
          rows={3}
          value={candidateAnswer}
          onChange={(e) => onAnswerChange(e.target.value)}
          placeholder={
            manualMode
              ? 'Type your answer here, then click Submit Answer...'
              : 'Speak your answer using the microphone, or type directly to edit prior to submission...'
          }
          className="w-full bg-slate-800/70 border border-slate-700/80 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
        />

        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>You can review, correct, or refine transcribed text before submission.</span>
          {candidateAnswer.length > 0 && (
            <button
              onClick={() => onAnswerChange('')}
              className="text-slate-400 hover:text-rose-400 transition cursor-pointer"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
