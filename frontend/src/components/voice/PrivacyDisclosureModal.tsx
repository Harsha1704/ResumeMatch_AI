import React from 'react';
import { ShieldCheck, Mic, Lock, EyeOff, Radio, Check } from 'lucide-react';

interface PrivacyDisclosureModalProps {
  isOpen: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

export const PrivacyDisclosureModal: React.FC<PrivacyDisclosureModalProps> = ({
  isOpen,
  onAccept,
  onDecline,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 sm:p-8 shadow-2xl space-y-6 text-slate-200">
        <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Voice & Privacy Disclosure</h2>
            <p className="text-xs text-slate-400">ResumeMatch AI Voice Interview Room • Strict ₹0 Architecture</p>
          </div>
        </div>

        <div className="space-y-4 text-xs text-slate-300">
          <div className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-800">
            <Mic className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Microphone Usage Only During Active Turn</p>
              <p className="text-slate-400 mt-0.5">
                Microphone audio is accessed solely when you click "Start Speaking" or keep active voice enabled. You have complete control to toggle the microphone off at any time.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-800">
            <Radio className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Browser-Dependent Speech Processing</p>
              <p className="text-slate-400 mt-0.5">
                Speech recognition is processed via your browser's native Web Speech API (e.g., Google Chrome speech services, Apple Safari, or Microsoft Edge). Processing characteristics depend on your browser vendor.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-800">
            <EyeOff className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Zero Raw Audio or Video Storage</p>
              <p className="text-slate-400 mt-0.5">
                ResumeMatch AI <strong>never</strong> records, streams, uploads, or retains raw audio recordings or webcam video. Only converted text transcripts are evaluated and stored in your local session.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-800">
            <Lock className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Manual Text Fallback Always Available</p>
              <p className="text-slate-400 mt-0.5">
                If you prefer not to use your microphone or if speech recognition is unavailable, you can switch to manual text input at any point with identical interview scoring.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-end gap-3">
          <button
            onClick={onDecline}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-medium transition cursor-pointer"
          >
            Use Manual Text Mode Only
          </button>
          <button
            onClick={onAccept}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Check className="w-4 h-4" />
            I Understand & Continue with Voice
          </button>
        </div>
      </div>
    </div>
  );
};
