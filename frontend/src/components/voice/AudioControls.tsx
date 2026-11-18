import React from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Play,
  Pause,
  RotateCcw,
  Send,
  Square,
  Sparkles,
  Loader2,
  Radio,
  FileText,
} from 'lucide-react';
import type { SpeechRecognitionStatus, SpeechSynthesisStatus } from '../../types/voice';

interface AudioControlsProps {
  sessionId: string | null;
  isListening: boolean;
  isSpeaking: boolean;
  isMuted: boolean;
  recognitionStatus: SpeechRecognitionStatus;
  synthesisStatus: SpeechSynthesisStatus;
  isSubmitting: boolean;
  hasAnswer: boolean;
  manualMode: boolean;
  onStartInterview: () => void;
  onToggleListening: () => void;
  onToggleMute: () => void;
  onPauseSpeech: () => void;
  onResumeSpeech: () => void;
  onReplayQuestion: () => void;
  onSubmitAnswer: () => void;
  onEndInterview: () => void;
  onToggleManualMode?: (manual: boolean) => void;
}

export const AudioControls: React.FC<AudioControlsProps> = ({
  sessionId,
  isListening,
  isSpeaking,
  isMuted,
  recognitionStatus,
  synthesisStatus,
  isSubmitting,
  hasAnswer,
  manualMode,
  onStartInterview,
  onToggleListening,
  onToggleMute,
  onPauseSpeech,
  onResumeSpeech,
  onReplayQuestion,
  onSubmitAnswer,
  onEndInterview,
  onToggleManualMode,
}) => {
  if (!sessionId) {
    return (
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">AI Voice Interview Room Ready</h3>
            <p className="text-xs text-slate-400">Browser-native speech engine • Strict ₹0 budget</p>
          </div>
        </div>
        <button
          onClick={onStartInterview}
          className="w-full sm:w-auto px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <Sparkles className="w-4 h-4" />
          Start Voice Interview
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-900/95 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-md"
      role="toolbar"
      aria-label="Interview Audio and Session Controls"
    >
      {/* Left controls: Mic toggle & Speech controls */}
      <div className="flex flex-wrap items-center gap-2">
        {!manualMode ? (
          <button
            onClick={onToggleListening}
            aria-label={isListening ? 'Turn off microphone' : 'Turn on microphone'}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition shadow-md cursor-pointer ${
              isListening
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse shadow-rose-600/30'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
            }`}
          >
            {isListening ? (
              <>
                <Mic className="w-4 h-4 text-white animate-bounce" />
                <span>Listening...</span>
              </>
            ) : (
              <>
                <MicOff className="w-4 h-4 text-slate-400" />
                <span>Mic Off</span>
              </>
            )}
          </button>
        ) : (
          <span className="px-3.5 py-2 bg-slate-800/80 border border-slate-700 text-slate-300 text-xs rounded-xl flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            Manual Text Mode
          </span>
        )}

        {/* Mute Interviewer Voice Toggle (Silences output without affecting microphone input) */}
        <button
          onClick={onToggleMute}
          aria-label={isMuted ? 'Unmute interviewer speech output' : 'Mute interviewer speech output'}
          title={isMuted ? 'Unmute interviewer speech output' : 'Mute interviewer speech output'}
          className={`p-2.5 rounded-xl border text-xs font-medium transition cursor-pointer ${
            isMuted
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20'
              : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
          }`}
        >
          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
        </button>

        {/* Pause/Resume Interviewer Speech Output */}
        {isSpeaking && (
          <button
            onClick={synthesisStatus === 'paused' ? onResumeSpeech : onPauseSpeech}
            aria-label={synthesisStatus === 'paused' ? 'Resume speaking' : 'Pause speaking'}
            title={synthesisStatus === 'paused' ? 'Resume speaking' : 'Pause speaking'}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 transition cursor-pointer"
          >
            {synthesisStatus === 'paused' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
        )}

        {/* Replay Question Button */}
        <button
          onClick={onReplayQuestion}
          aria-label="Replay current question audio"
          title="Replay current question audio"
          className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-slate-300 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
          <span className="hidden sm:inline">Replay</span>
        </button>

        {/* Manual Text Fallback Toggle */}
        {onToggleManualMode && (
          <button
            onClick={() => onToggleManualMode(!manualMode)}
            aria-label={manualMode ? 'Switch to Voice Mode' : 'Switch to Text Mode'}
            title={manualMode ? 'Switch to Voice Mode' : 'Switch to Text Mode'}
            className="px-3 py-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl text-slate-300 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden md:inline">{manualMode ? 'Voice Mode' : 'Text Fallback'}</span>
          </button>
        )}
      </div>

      {/* Right controls: Submit Answer & End Session */}
      <div className="flex items-center gap-2">
        <button
          onClick={onSubmitAnswer}
          disabled={!hasAnswer || isSubmitting}
          aria-label="Submit your answer for evaluation"
          className={`px-5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition shadow-md cursor-pointer ${
            hasAnswer && !isSubmitting
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30'
              : 'bg-slate-800 text-slate-500 border border-slate-800 cursor-not-allowed'
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Scoring Answer...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Submit Answer</span>
            </>
          )}
        </button>

        <button
          onClick={onEndInterview}
          aria-label="Conclude interview session"
          title="Conclude interview session"
          className="px-3.5 py-2 bg-slate-800/80 hover:bg-rose-500/20 hover:text-rose-300 hover:border-rose-500/30 border border-slate-700 rounded-xl text-slate-400 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
        >
          <Square className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">End</span>
        </button>
      </div>
    </div>
  );
};
