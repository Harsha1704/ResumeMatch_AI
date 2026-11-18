import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mic,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Award,
  RotateCcw,
  BookOpen,
  ArrowRight,
  Radio,
  Sliders,
  Cpu,
  Activity,
  Headphones,
  Check,
} from 'lucide-react';
import { useAnalysis } from '../context/AnalysisContext';
import { useVoiceInterview } from '../hooks/useVoiceInterview';
import { InterviewHeaderBar } from '../components/voice/InterviewHeaderBar';
import { InterviewerAvatar, type AvatarState } from '../components/voice/InterviewerAvatar';
import { VoiceWaveform, type WaveformMode } from '../components/voice/VoiceWaveform';
import { AudioControls } from '../components/voice/AudioControls';
import { CandidateWebcamPreview } from '../components/voice/CandidateWebcamPreview';
import { LiveTranscript } from '../components/voice/LiveTranscript';
import { PrivacyDisclosureModal } from '../components/voice/PrivacyDisclosureModal';
import { BrowserCompatibilityBanner } from '../components/voice/BrowserCompatibilityBanner';

export const VoiceInterviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentAnalysis } = useAnalysis();

  const [roleInput, setRoleInput] = useState<string>(
    currentAnalysis?.job_title || currentAnalysis?.detected_job_title || 'Software Engineer'
  );
  const [difficultyInput, setDifficultyInput] = useState<string>('all');
  const [questionCountInput, setQuestionCountInput] = useState<number>(3);
  const [showPrivacyModal, setShowPrivacyModal] = useState<boolean>(false);

  const {
    sessionId,
    targetRole,
    difficulty,
    totalQuestions,
    currentIndex,
    currentQuestion,
    isCompleted,
    finalReport,
    candidateAnswer,
    interimSpeech,
    isListening,
    isSpeaking,
    isMuted,
    recognitionStatus,
    synthesisStatus,
    transcript,
    isSubmitting,
    hasFollowup,
    errorMessage,
    isPermissionDenied,
    manualMode,
    capabilities,
    startInterview,
    toggleListening,
    toggleMute,
    pauseSpeech,
    resumeSpeech,
    replayQuestion,
    updateCandidateAnswer,
    submitAnswer,
    requestFollowup,
    endInterview,
    setManualMode,
    setPrivacyAccepted,
  } = useVoiceInterview();

  // Derive real active states for avatar & waveform
  const currentAvatarState: AvatarState = isSubmitting
    ? 'thinking'
    : isSpeaking
    ? 'speaking'
    : isListening
    ? 'listening'
    : 'idle';

  const currentWaveformMode: WaveformMode = isSubmitting
    ? 'thinking'
    : isSpeaking
    ? 'speaking'
    : isListening
    ? 'listening'
    : 'idle';

  const handleStart = async () => {
    await startInterview({
      target_role: roleInput,
      difficulty: difficultyInput,
      max_questions: questionCountInput,
      analysis_id: currentAnalysis?.analysis_id,
      job_description: currentAnalysis?.job_description_text || currentAnalysis?.raw_jd,
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      {/* Header Bar with Elapsed Timer & Progress */}
      <InterviewHeaderBar
        sessionId={sessionId}
        targetRole={sessionId ? targetRole : roleInput}
        difficulty={sessionId ? difficulty : difficultyInput}
        currentIndex={currentIndex}
        totalQuestions={totalQuestions}
        isCompleted={isCompleted}
        onOpenPrivacy={() => setShowPrivacyModal(true)}
        onEndInterview={endInterview}
      />

      {/* Browser Speech Compatibility Banner */}
      <BrowserCompatibilityBanner
        capabilities={capabilities}
        isPermissionDenied={isPermissionDenied}
        manualMode={manualMode}
        onToggleManualMode={setManualMode}
      />

      {/* Error Alert Display */}
      {errorMessage && (
        <div
          className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-300 text-xs flex items-center gap-3 animate-in fade-in duration-200"
          role="alert"
        >
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Setup View (Before Session Start) */}
      {!sessionId && !isCompleted && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Configuration Card */}
          <div className="lg:col-span-7 p-6 sm:p-8 bg-slate-900/90 border border-slate-800 rounded-3xl shadow-2xl backdrop-blur-md space-y-6">
            <div className="space-y-1.5">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-indigo-400" />
                <span>Configure Your Interview Simulation</span>
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Select your targeted position and difficulty level. The AI interviewer will generate role-tailored behavioral and technical questions scored against STAR benchmarks.
              </p>
            </div>

            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold">Target Position / Role</label>
                <input
                  type="text"
                  value={roleInput}
                  onChange={(e) => setRoleInput(e.target.value)}
                  placeholder="e.g. Senior Frontend Engineer, Staff Data Scientist"
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Difficulty Level</label>
                  <select
                    value={difficultyInput}
                    onChange={(e) => setDifficultyInput(e.target.value)}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  >
                    <option value="all">Mixed (Adaptive Evaluation)</option>
                    <option value="easy">Easy (Fundamentals & Background)</option>
                    <option value="medium">Medium (Standard Competencies)</option>
                    <option value="hard">Hard (Advanced Architecture)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Number of Questions</label>
                  <select
                    value={questionCountInput}
                    onChange={(e) => setQuestionCountInput(Number(e.target.value))}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"
                  >
                    <option value={3}>3 Questions (Quick Sprint)</option>
                    <option value={5}>5 Questions (Standard Practice)</option>
                    <option value={8}>8 Questions (In-Depth Simulation)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={handleStart}
                className="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold rounded-2xl shadow-xl shadow-indigo-600/30 flex items-center justify-center gap-2 text-sm transition cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>Begin Voice Interview Room</span>
              </button>
            </div>
          </div>

          {/* Right Column: Engine Features & Privacy Assurances */}
          <div className="lg:col-span-5 p-6 sm:p-8 bg-slate-900/60 border border-slate-800/80 rounded-3xl space-y-5">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider text-slate-400">
              Zero-Cloud Cost Architecture
            </h3>

            <div className="space-y-4 text-xs text-slate-300">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400 shrink-0">
                  <Headphones className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Browser-Native Speech</h4>
                  <p className="text-slate-400 mt-0.5">
                    Utilizes W3C SpeechRecognition and SpeechSynthesis with zero external cloud speech APIs or paid usage tokens.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400 shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Zero Audio Retention</h4>
                  <p className="text-slate-400 mt-0.5">
                    Microphone audio is transcribed directly in-browser. Raw audio files and webcam streams are never stored or transmitted.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 bg-cyan-500/10 rounded-xl text-cyan-400 shrink-0">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Local Heuristic Scoring</h4>
                  <p className="text-slate-400 mt-0.5">
                    Evaluates responses against STAR criteria, keyword relevancy, and communicative clarity without paid external LLMs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Room View (Interview in Progress) */}
      {sessionId && !isCompleted && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Visual Stage (Avatar + Waveform + Controls) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="p-6 sm:p-8 bg-slate-900/90 border border-slate-800 rounded-3xl shadow-2xl backdrop-blur-md space-y-6 flex flex-col items-center">
              {/* AI Interviewer Avatar */}
              <InterviewerAvatar
                state={currentAvatarState}
                interviewerName="ResumeMatch AI"
                isMuted={isMuted}
              />

              {/* Real-time Voice Waveform Activity */}
              <VoiceWaveform mode={currentWaveformMode} />
            </div>

            {/* Optional Candidate Webcam Preview & Visual Presence Checks */}
            <CandidateWebcamPreview isInterviewCompleted={isCompleted} />

            {/* Audio Controls Toolbar */}
            <AudioControls
              sessionId={sessionId}
              isListening={isListening}
              isSpeaking={isSpeaking}
              isMuted={isMuted}
              recognitionStatus={recognitionStatus}
              synthesisStatus={synthesisStatus}
              isSubmitting={isSubmitting}
              hasAnswer={candidateAnswer.trim().length > 0}
              manualMode={manualMode}
              onStartInterview={handleStart}
              onToggleListening={toggleListening}
              onToggleMute={toggleMute}
              onPauseSpeech={pauseSpeech}
              onResumeSpeech={resumeSpeech}
              onReplayQuestion={replayQuestion}
              onSubmitAnswer={submitAnswer}
              onEndInterview={endInterview}
              onToggleManualMode={setManualMode}
            />
          </div>

          {/* Right Column: Live Transcript & Candidate Answer Editor */}
          <div className="lg:col-span-7">
            <LiveTranscript
              transcript={transcript}
              currentQuestion={currentQuestion}
              currentIndex={currentIndex}
              totalQuestions={totalQuestions}
              candidateAnswer={candidateAnswer}
              interimSpeech={interimSpeech}
              isListening={isListening}
              recognitionStatus={recognitionStatus}
              manualMode={manualMode}
              onAnswerChange={updateCandidateAnswer}
              onSubmitAnswer={submitAnswer}
              onRequestFollowup={requestFollowup}
              hasFollowup={hasFollowup}
            />
          </div>
        </div>
      )}

      {/* Completed View (Final Scorecard & Analytics) */}
      {isCompleted && (
        <div className="p-8 sm:p-10 bg-slate-900/95 border border-slate-800 rounded-3xl shadow-2xl space-y-8 animate-in fade-in duration-300">
          <div className="text-center space-y-2">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-lg">
              <Award className="w-7 h-7" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Interview Completed!</h2>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Your spoken answers were transcribed and scored across STAR structure, keyword coverage, and role relevance.
            </p>
          </div>

          {finalReport && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-800">
              <div className="p-5 bg-slate-800/40 rounded-2xl border border-slate-800 text-center space-y-1">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                  Overall Score
                </span>
                <p className="text-3xl font-extrabold text-emerald-400">
                  {Math.round(finalReport.overall_score ?? 82)}%
                </p>
              </div>

              <div className="p-5 bg-slate-800/40 rounded-2xl border border-slate-800 text-center space-y-1">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                  Questions Answered
                </span>
                <p className="text-3xl font-extrabold text-white">
                  {finalReport.total_questions_completed ?? totalQuestions}
                </p>
              </div>

              <div className="p-5 bg-slate-800/40 rounded-2xl border border-slate-800 text-center space-y-1">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                  Speech Engine Cost
                </span>
                <p className="text-3xl font-extrabold text-indigo-400">₹0.00</p>
              </div>
            </div>
          )}

          {/* Transcript History Review */}
          <div className="space-y-3 pt-4 border-t border-slate-800">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Complete Session Transcript ({transcript.length} turns)
            </h3>
            <div className="max-h-72 overflow-y-auto p-4 sm:p-5 bg-slate-950/60 rounded-2xl border border-slate-800/80 space-y-3 text-xs">
              {transcript.map((entry) => (
                <div key={entry.entry_id} className="space-y-1">
                  <div className="flex items-center gap-2 text-[10px] text-slate-400">
                    <span className="font-bold text-slate-200 capitalize">{entry.speaker}:</span>
                    <span className="text-slate-500 font-mono">({entry.message_type})</span>
                  </div>
                  <p className="text-slate-300 pl-3 border-l-2 border-slate-800 leading-relaxed">
                    {entry.message_text}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Post-Session Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4 border-t border-slate-800">
            <button
              onClick={() => window.location.reload()}
              className="w-full sm:w-auto px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Practice Another Session</span>
            </button>
            <button
              onClick={() => navigate('/interview-results')}
              className="w-full sm:w-auto px-6 py-3 rounded-2xl border border-slate-700 hover:bg-slate-800 text-slate-300 text-xs font-medium flex items-center justify-center gap-2 transition cursor-pointer"
            >
              <BookOpen className="w-4 h-4" />
              <span>View Full Analytics</span>
            </button>
          </div>
        </div>
      )}

      {/* Privacy & Audio Permissions Modal */}
      <PrivacyDisclosureModal
        isOpen={showPrivacyModal}
        onAccept={() => {
          setPrivacyAccepted(true);
          setShowPrivacyModal(false);
        }}
        onDecline={() => {
          setManualMode(true);
          setShowPrivacyModal(false);
        }}
      />
    </div>
  );
};

export default VoiceInterviewPage;
