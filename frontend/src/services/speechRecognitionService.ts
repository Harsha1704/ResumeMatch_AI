/**
 * Browser-Native Speech Recognition Service.
 * Implements W3C SpeechRecognition / webkitSpeechRecognition.
 * Strict ₹0 Budget: 100% Client-Side Browser Speech Engine.
 */

import type { SpeechRecognitionStatus } from '../types/voice';

// Global window declarations for browser compatibility
interface IWindowWithSpeech extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export interface SpeechRecognitionCallbacks {
  onInterimTranscript?: (text: string) => void;
  onFinalTranscript?: (text: string) => void;
  onStatusChange?: (status: SpeechRecognitionStatus) => void;
  onError?: (errorMessage: string, isPermissionError: boolean) => void;
}

export class SpeechRecognitionService {
  private recognition: any = null;
  private isListening = false;
  private status: SpeechRecognitionStatus = 'idle';
  private callbacks: SpeechRecognitionCallbacks = {};
  private currentTranscript = '';
  private interimTranscript = '';
  private timeoutId: any = null;

  constructor(callbacks: SpeechRecognitionCallbacks = {}) {
    this.callbacks = callbacks;
    this.initEngine();
  }

  public static isSupported(): boolean {
    if (typeof window === 'undefined') return false;
    const win = window as IWindowWithSpeech;
    return Boolean(win.SpeechRecognition || win.webkitSpeechRecognition);
  }

  public static getEngineName(): 'SpeechRecognition' | 'webkitSpeechRecognition' | 'none' {
    if (typeof window === 'undefined') return 'none';
    const win = window as IWindowWithSpeech;
    if (win.SpeechRecognition) return 'SpeechRecognition';
    if (win.webkitSpeechRecognition) return 'webkitSpeechRecognition';
    return 'none';
  }

  private setStatus(newStatus: SpeechRecognitionStatus): void {
    this.status = newStatus;
    if (this.callbacks.onStatusChange) {
      this.callbacks.onStatusChange(newStatus);
    }
  }

  private initEngine(): void {
    if (!SpeechRecognitionService.isSupported()) {
      this.setStatus('unsupported');
      return;
    }

    try {
      const win = window as IWindowWithSpeech;
      const RecognitionConstructor = win.SpeechRecognition || win.webkitSpeechRecognition;
      this.recognition = new RecognitionConstructor();

      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';
      this.recognition.maxAlternatives = 1;

      this.recognition.onstart = () => {
        this.isListening = true;
        this.setStatus('listening');
      };

      this.recognition.onresult = (event: any) => {
        let interim = '';
        let finalizedThisTurn = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          const transcriptPiece = result[0].transcript;
          if (result.isFinal) {
            finalizedThisTurn += transcriptPiece;
          } else {
            interim += transcriptPiece;
          }
        }

        if (finalizedThisTurn) {
          const spacing = this.currentTranscript.length > 0 ? ' ' : '';
          this.currentTranscript += spacing + finalizedThisTurn.trim();
          if (this.callbacks.onFinalTranscript) {
            this.callbacks.onFinalTranscript(this.currentTranscript);
          }
        }

        this.interimTranscript = interim;
        if (this.callbacks.onInterimTranscript) {
          this.callbacks.onInterimTranscript(interim);
        }
      };

      this.recognition.onerror = (event: any) => {
        const error = event.error || 'unknown-error';
        let userMessage = 'Speech recognition error occurred.';
        let isPermissionError = false;

        switch (error) {
          case 'not-allowed':
          case 'service-not-allowed':
            userMessage = 'Microphone permission was denied. Please allow microphone access in your browser settings to speak answers.';
            isPermissionError = true;
            break;
          case 'no-speech':
            // Non-fatal silence notification; do not break session
            return;
          case 'audio-capture':
            userMessage = 'No microphone was detected on your device. Please connect an audio input device.';
            break;
          case 'network':
            userMessage = 'Browser speech recognition network error. Ensure internet connectivity or switch to text answer mode.';
            break;
          case 'aborted':
            return;
          default:
            userMessage = `Speech recognition error: ${error}.`;
        }

        this.setStatus('error');
        if (this.callbacks.onError) {
          this.callbacks.onError(userMessage, isPermissionError);
        }
      };

      this.recognition.onend = () => {
        // If we are still supposed to be listening (e.g. continuous mode in Chrome), auto-restart unless stopped
        if (this.isListening) {
          try {
            this.recognition.start();
          } catch (e) {
            this.isListening = false;
            this.setStatus('idle');
          }
        } else {
          this.setStatus('idle');
        }
      };
    } catch (e: any) {
      this.setStatus('error');
      if (this.callbacks.onError) {
        this.callbacks.onError(`Failed to initialize speech recognition: ${e.message}`, false);
      }
    }
  }

  public startListening(): Promise<boolean> {
    if (!this.recognition) {
      if (this.callbacks.onError) {
        this.callbacks.onError('Speech recognition is not supported in this browser.', false);
      }
      return Promise.resolve(false);
    }

    if (this.isListening) {
      return Promise.resolve(true);
    }

    this.setStatus('requesting_permission');
    this.isListening = true;

    try {
      this.recognition.start();
      return Promise.resolve(true);
    } catch (e: any) {
      // If already started or browser throws
      if (e.name === 'InvalidStateError') {
        this.setStatus('listening');
        return Promise.resolve(true);
      }
      this.isListening = false;
      this.setStatus('error');
      if (this.callbacks.onError) {
        this.callbacks.onError(`Could not start speech recognition: ${e.message}`, false);
      }
      return Promise.resolve(false);
    }
  }

  public stopListening(): void {
    this.isListening = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {
        // Ignored if already stopped
      }
    }
    this.setStatus('idle');
  }

  public abort(): void {
    this.isListening = false;
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (e) {
        // Ignored
      }
    }
    this.setStatus('idle');
    this.currentTranscript = '';
    this.interimTranscript = '';
  }

  public resetTranscript(): void {
    this.currentTranscript = '';
    this.interimTranscript = '';
    if (this.callbacks.onFinalTranscript) {
      this.callbacks.onFinalTranscript('');
    }
    if (this.callbacks.onInterimTranscript) {
      this.callbacks.onInterimTranscript('');
    }
  }

  public getStatus(): SpeechRecognitionStatus {
    return this.status;
  }

  public isListeningState(): boolean {
    return this.isListening;
  }

  public getRecognitionInstance(): any {
    return this.recognition;
  }

  public getTranscript(): string {
    return this.currentTranscript;
  }

  public setCallbacks(callbacks: SpeechRecognitionCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  public destroy(): void {
    this.abort();
    this.recognition = null;
    this.callbacks = {};
  }
}
