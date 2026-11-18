import React from 'react';
import { AlertCircle, MicOff, Info, CheckCircle2 } from 'lucide-react';
import type { BrowserSpeechCapabilities } from '../../types/voice';

interface BrowserCompatibilityBannerProps {
  capabilities: BrowserSpeechCapabilities;
  isPermissionDenied: boolean;
  manualMode: boolean;
  onToggleManualMode: (enabled: boolean) => void;
}

export const BrowserCompatibilityBanner: React.FC<BrowserCompatibilityBannerProps> = ({
  capabilities,
  isPermissionDenied,
  manualMode,
  onToggleManualMode,
}) => {
  if (capabilities.speechRecognitionSupported && !isPermissionDenied && !manualMode) {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-3 flex items-center justify-between text-xs text-emerald-300">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>
            <strong>Voice Engine Active:</strong> Browser speech recognition ({capabilities.recognitionEngine}) & synthesis are fully supported.
          </span>
        </div>
        <button
          onClick={() => onToggleManualMode(true)}
          className="text-emerald-400 hover:text-emerald-300 underline font-medium cursor-pointer"
        >
          Switch to Manual Text Mode
        </button>
      </div>
    );
  }

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-amber-200">
      <div className="flex items-start gap-3">
        {isPermissionDenied ? (
          <MicOff className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        ) : (
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        )}
        <div className="flex-1 text-xs space-y-1">
          <p className="font-semibold text-amber-300 text-sm">
            {isPermissionDenied
              ? 'Microphone Access Denied — Manual Mode Enabled'
              : !capabilities.speechRecognitionSupported
              ? 'Speech Recognition Unavailable in this Browser'
              : 'Manual Text Fallback Active'}
          </p>
          <p className="text-amber-200/80 leading-relaxed">
            {isPermissionDenied
              ? 'You blocked microphone permission or your device has no audio input. You can type your answers directly into the transcript editor below.'
              : !capabilities.speechRecognitionSupported
              ? 'This browser does not support the W3C Web Speech Recognition API (recommended: Chrome, Edge, or Safari). You can participate fully using manual text responses.'
              : 'Manual mode is enabled. Spoken questions will still be audible via speech synthesis, and you can type your answers.'}
          </p>
          <div className="pt-2 flex items-center gap-4">
            {capabilities.speechRecognitionSupported && !isPermissionDenied && manualMode && (
              <button
                onClick={() => onToggleManualMode(false)}
                className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                Enable Voice Recognition
              </button>
            )}
            <span className="text-amber-300/60 flex items-center gap-1">
              <Info className="w-3.5 h-3.5" />
              Strict ₹0 architecture • No external speech APIs called
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
