/**
 * Browser-Native Speech Synthesis Service.
 * Implements W3C Web Speech API window.speechSynthesis.
 * Strict ₹0 Budget: 100% Client-Side Audio Playback.
 */

import type { SpeechSynthesisStatus } from '../types/voice';

export interface SpeechSynthesisCallbacks {
  onStart?: () => void;
  onEnd?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: SpeechSynthesisStatus) => void;
}

export interface SpeechOptions {
  rate?: number; // 0.5 to 2.0 (default 1.0)
  pitch?: number; // 0.5 to 1.5 (default 1.0)
  volume?: number; // 0.0 to 1.0 (default 1.0)
  voiceURI?: string;
}

export class SpeechSynthesisService {
  private isMuted = false;
  private status: SpeechSynthesisStatus = 'idle';
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private lastSpokenText = '';
  private lastOptions: SpeechOptions = {};
  private callbacks: SpeechSynthesisCallbacks = {};
  private availableVoices: SpeechSynthesisVoice[] = [];
  private selectedVoice: SpeechSynthesisVoice | null = null;

  // Default audio tuning for clean professional interviewer tone
  private rate = 1.0;
  private pitch = 1.0;
  private volume = 1.0;

  constructor(callbacks: SpeechSynthesisCallbacks = {}) {
    this.callbacks = callbacks;
    this.initVoices();
  }

  public static isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  }

  private setStatus(newStatus: SpeechSynthesisStatus): void {
    this.status = newStatus;
    if (this.callbacks.onStatusChange) {
      this.callbacks.onStatusChange(newStatus);
    }
  }

  private initVoices(): void {
    if (!SpeechSynthesisService.isSupported()) {
      return;
    }

    const loadVoices = () => {
      try {
        const voices = window.speechSynthesis.getVoices();
        if (voices && voices.length > 0) {
          this.availableVoices = voices;
          // Prefer natural English voices
          const preferred = voices.find(
            (v) =>
              (v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel') || v.name.includes('Premium')))
          ) || voices.find((v) => v.lang.startsWith('en')) || voices[0];
          this.selectedVoice = preferred || null;
        }
      } catch (e) {
        // Ignored
      }
    };

    loadVoices();
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  public getVoices(): SpeechSynthesisVoice[] {
    if (this.availableVoices.length === 0) {
      this.initVoices();
    }
    return this.availableVoices;
  }

  public setVoice(voiceURI: string): void {
    const found = this.availableVoices.find((v) => v.voiceURI === voiceURI);
    if (found) {
      this.selectedVoice = found;
    }
  }

  public setRate(rate: number): void {
    this.rate = Math.max(0.5, Math.min(2.0, rate));
  }

  public setVolume(volume: number): void {
    this.volume = Math.max(0.0, Math.min(1.0, volume));
  }

  public setMuted(muted: boolean): void {
    this.isMuted = muted;
    if (muted && this.status === 'speaking') {
      this.cancel();
      this.setStatus('muted');
    } else if (!muted && this.status === 'muted') {
      this.setStatus('idle');
    }
  }

  public isCurrentlyMuted(): boolean {
    return this.isMuted;
  }

  public isMutedState(): boolean {
    return this.isMuted;
  }

  public speak(text: string, options: SpeechOptions = {}): Promise<void> {
    if (!SpeechSynthesisService.isSupported()) {
      return Promise.resolve();
    }

    // Always stop ongoing speech to avoid overlapping audio
    this.cancel();

    if (!text || !text.trim()) {
      return Promise.resolve();
    }

    this.lastSpokenText = text;
    this.lastOptions = options;

    if (this.isMuted) {
      this.setStatus('muted');
      if (this.callbacks.onStart) this.callbacks.onStart();
      if (this.callbacks.onEnd) this.callbacks.onEnd();
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      try {
        const utterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance = utterance;

        utterance.rate = options.rate !== undefined ? options.rate : this.rate;
        utterance.pitch = options.pitch !== undefined ? options.pitch : this.pitch;
        utterance.volume = options.volume !== undefined ? options.volume : this.volume;

        if (options.voiceURI) {
          const v = this.availableVoices.find((voice) => voice.voiceURI === options.voiceURI);
          if (v) utterance.voice = v;
        } else if (this.selectedVoice) {
          utterance.voice = this.selectedVoice;
        }

        utterance.onstart = () => {
          this.setStatus('speaking');
          if (this.callbacks.onStart) this.callbacks.onStart();
        };

        utterance.onend = () => {
          this.currentUtterance = null;
          this.setStatus('idle');
          if (this.callbacks.onEnd) this.callbacks.onEnd();
          resolve();
        };

        utterance.onerror = (event: any) => {
          this.currentUtterance = null;
          this.setStatus('idle');
          const errorMsg = event.error || 'speech-synthesis-error';
          // 'canceled' or 'interrupted' is expected when switching turns
          if (errorMsg !== 'canceled' && errorMsg !== 'interrupted') {
            if (this.callbacks.onError) this.callbacks.onError(errorMsg);
          }
          resolve();
        };

        utterance.onpause = () => {
          this.setStatus('paused');
          if (this.callbacks.onPause) this.callbacks.onPause();
        };

        utterance.onresume = () => {
          this.setStatus('speaking');
          if (this.callbacks.onResume) this.callbacks.onResume();
        };

        window.speechSynthesis.speak(utterance);
      } catch (e: any) {
        this.setStatus('idle');
        if (this.callbacks.onError) {
          this.callbacks.onError(`Speech synthesis failed: ${e.message}`);
        }
        resolve();
      }
    });
  }

  public pause(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    if (this.status === 'speaking') {
      window.speechSynthesis.pause();
      this.setStatus('paused');
    }
  }

  public resume(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    if (this.status === 'paused') {
      window.speechSynthesis.resume();
      this.setStatus('speaking');
    }
  }

  public cancel(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    try {
      window.speechSynthesis.cancel();
    } catch (e) {
      // Ignored
    }
    this.currentUtterance = null;
    this.setStatus(this.isMuted ? 'muted' : 'idle');
  }

  public replay(): Promise<void> {
    if (this.lastSpokenText) {
      return this.speak(this.lastSpokenText, this.lastOptions);
    }
    return Promise.resolve();
  }

  public getStatus(): SpeechSynthesisStatus {
    return this.status;
  }

  public setCallbacks(callbacks: SpeechSynthesisCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  public destroy(): void {
    this.cancel();
    this.callbacks = {};
  }
}
