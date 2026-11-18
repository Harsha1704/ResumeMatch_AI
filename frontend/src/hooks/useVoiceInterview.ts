/**
 * Custom React Hook for AI Voice Interview Room (Phase 4).
 * Coordinates browser speech recognition, text-to-speech synthesis,
 * conversational state machine, and backend persistence.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import { SpeechRecognitionService } from '../services/speechRecognitionService';
import { SpeechSynthesisService } from '../services/speechSynthesisService';
import type {
  SpeechRecognitionStatus,
  SpeechSynthesisStatus,
  BrowserSpeechCapabilities,
  VoiceTranscriptEntry,
  VoiceStartPayload,
  VoiceAnswerResponse,
  VoiceEndResponse,
} from '../types/voice';

export function useVoiceInterview() {
  // Session & Question state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [targetRole, setTargetRole] = useState<string>('Software Engineer');
  const [difficulty, setDifficulty] = useState<string>('all');
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [currentQuestion, setCurrentQuestion] = useState<any>(null);

  // Audio & Transcription state
  const [candidateAnswer, setCandidateAnswer] = useState<string>('');
  const [interimSpeech, setInterimSpeech] = useState<string>('');
  const [recognitionStatus, setRecognitionStatus] = useState<SpeechRecognitionStatus>('idle');
  const [synthesisStatus, setSynthesisStatus] = useState<SpeechSynthesisStatus>('idle');
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);

  // Conversation & Persistence state
  const [transcript, setTranscript] = useState<VoiceTranscriptEntry[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [hasFollowup, setHasFollowup] = useState<boolean>(false);
  const [followupData, setFollowupData] = useState<any>(null);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [finalReport, setFinalReport] = useState<any>(null);

  // Browser & Privacy state
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPermissionDenied, setIsPermissionDenied] = useState<boolean>(false);
  const [manualMode, setManualMode] = useState<boolean>(false);
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);

  // Capabilities
  const [capabilities, setCapabilities] = useState<BrowserSpeechCapabilities>({
    speechRecognitionSupported: false,
    speechSynthesisSupported: false,
    recognitionEngine: 'none',
    availableVoicesCount: 0,
  });

  // Service singletons held in refs to persist across re-renders
  const recognitionRef = useRef<SpeechRecognitionService | null>(null);
  const synthesisRef = useRef<SpeechSynthesisService | null>(null);

  // Initialize capabilities and services on mount
  useEffect(() => {
    const recogSupported = SpeechRecognitionService.isSupported();
    const synthSupported = SpeechSynthesisService.isSupported();
    const engineName = SpeechRecognitionService.getEngineName();

    setCapabilities({
      speechRecognitionSupported: recogSupported,
      speechSynthesisSupported: synthSupported,
      recognitionEngine: engineName,
      availableVoicesCount: 0,
    });

    if (!recogSupported) {
      setManualMode(true);
    }

    // Initialize Synthesis Service
    synthesisRef.current = new SpeechSynthesisService({
      onStart: () => setIsSpeaking(true),
      onEnd: () => setIsSpeaking(false),
      onStatusChange: (status) => {
        setSynthesisStatus(status);
        setIsSpeaking(status === 'speaking');
      },
      onError: (err) => {
        setIsSpeaking(false);
        console.warn('Speech synthesis warning:', err);
      },
    });

    // Initialize Recognition Service
    recognitionRef.current = new SpeechRecognitionService({
      onInterimTranscript: (interim) => {
        setInterimSpeech(interim);
      },
      onFinalTranscript: (finalText) => {
        setCandidateAnswer(finalText);
        setInterimSpeech('');
      },
      onStatusChange: (status) => {
        setRecognitionStatus(status);
        setIsListening(status === 'listening');
      },
      onError: (err, isPerm) => {
        setErrorMessage(err);
        setIsListening(false);
        if (isPerm) {
          setIsPermissionDenied(true);
          setManualMode(true);
        }
      },
    });

    return () => {
      // Clean up on component unmount
      if (recognitionRef.current) {
        recognitionRef.current.destroy();
      }
      if (synthesisRef.current) {
        synthesisRef.current.destroy();
      }
    };
  }, []);

  // Update voice count once voices load
  useEffect(() => {
    if (synthesisRef.current) {
      const voices = synthesisRef.current.getVoices();
      if (voices && voices.length > 0) {
        setCapabilities((prev) => ({
          ...prev,
          availableVoicesCount: voices.length,
        }));
      }
    }
  }, []);

  /**
   * Appends an entry to the live transcript state in memory.
   */
  const addTranscriptMessage = useCallback(
    (speaker: 'interviewer' | 'candidate', type: any, text: string) => {
      const newEntry: VoiceTranscriptEntry = {
        entry_id: `client_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        session_id: sessionId || '',
        speaker,
        message_type: type,
        message_text: text,
        timestamp: Date.now() / 1000,
        sequence_order: transcript.length + 1,
      };
      setTranscript((prev) => [...prev, newEntry]);
    },
    [sessionId, transcript.length]
  );

  /**
   * Starts a new voice interview session.
   */
  const startInterview = useCallback(
    async (payload: VoiceStartPayload = {}) => {
      setErrorMessage(null);
      setIsCompleted(false);
      setFinalReport(null);
      setTranscript([]);
      setCandidateAnswer('');
      setInterimSpeech('');
      setHasFollowup(false);
      setFollowupData(null);

      try {
        const res = await api.startVoiceSession(payload);
        if (res.status !== 'success') {
          throw new Error(res.message || 'Failed to start voice interview session.');
        }

        setSessionId(res.session_id);
        setTargetRole(res.target_role);
        setDifficulty(res.difficulty);
        setTotalQuestions(res.total_questions);
        setCurrentIndex(0);
        setCurrentQuestion(res.current_question);

        // Record initial interviewer greeting in transcript
        addTranscriptMessage('interviewer', 'greeting', res.interviewer_speech);

        // Speak interviewer greeting and question aloud via TTS
        if (synthesisRef.current) {
          await synthesisRef.current.speak(res.interviewer_speech);
        }

        // Auto-start listening if recognition is supported and not in manual mode
        if (!manualMode && recognitionRef.current && SpeechRecognitionService.isSupported()) {
          await recognitionRef.current.startListening();
        }

        return res;
      } catch (err: any) {
        const msg = err.message || 'Error starting voice interview.';
        setErrorMessage(msg);
        throw err;
      }
    },
    [addTranscriptMessage, manualMode]
  );

  /**
   * Starts listening for candidate speech.
   */
  const startListening = useCallback(async () => {
    setErrorMessage(null);
    if (synthesisRef.current) {
      synthesisRef.current.cancel(); // Mute interviewer when candidate speaks
    }
    if (recognitionRef.current) {
      const started = await recognitionRef.current.startListening();
      if (!started && !SpeechRecognitionService.isSupported()) {
        setManualMode(true);
      }
    }
  }, []);

  /**
   * Stops listening for candidate speech.
   */
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stopListening();
    }
  }, []);

  /**
   * Toggles microphone listening state.
   */
  const toggleListening = useCallback(async () => {
    if (isListening) {
      stopListening();
    } else {
      await startListening();
    }
  }, [isListening, startListening, stopListening]);

  /**
   * Toggles interviewer mute state.
   */
  const toggleMute = useCallback(() => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (synthesisRef.current) {
      synthesisRef.current.setMuted(nextMuted);
    }
  }, [isMuted]);

  /**
   * Pauses interviewer speech synthesis.
   */
  const pauseSpeech = useCallback(() => {
    if (synthesisRef.current) {
      synthesisRef.current.pause();
    }
  }, []);

  /**
   * Resumes interviewer speech synthesis.
   */
  const resumeSpeech = useCallback(() => {
    if (synthesisRef.current) {
      synthesisRef.current.resume();
    }
  }, []);

  /**
   * Replays current question prompt aloud.
   */
  const replayQuestion = useCallback(async () => {
    if (synthesisRef.current && currentQuestion) {
      const qText = currentQuestion.question_text || '';
      const prompt = `Question ${currentIndex + 1} of ${totalQuestions}: ${qText}`;
      await synthesisRef.current.speak(prompt);
    }
  }, [currentIndex, currentQuestion, totalQuestions]);

  /**
   * Updates candidate answer text (allowing manual editing before submission).
   */
  const updateCandidateAnswer = useCallback((text: string) => {
    setCandidateAnswer(text);
  }, []);


  /**
   * Concludes the voice interview session.
   */
  const endInterview = useCallback(async () => {
    if (!sessionId) return;
    stopListening();
    if (synthesisRef.current) {
      synthesisRef.current.cancel();
    }

    try {
      const res: VoiceEndResponse = await api.endVoiceSession(sessionId);
      if (res.status === 'success') {
        setIsCompleted(true);
        setFinalReport(res.final_report || res.results);

        // Add closing remark to transcript
        addTranscriptMessage('interviewer', 'closing', res.interviewer_speech);

        // Speak closing remark aloud
        if (synthesisRef.current) {
          await synthesisRef.current.speak(res.interviewer_speech);
        }
      }
      return res;
    } catch (err: any) {
      setErrorMessage(err.message || 'Error concluding interview session.');
    }
  }, [addTranscriptMessage, sessionId, stopListening]);

  /**
   * Submits candidate's answer to the local backend.
   */
  const submitAnswer = useCallback(async () => {
    if (!sessionId) {
      setErrorMessage('No active voice interview session.');
      return;
    }

    const answerToSubmit = candidateAnswer.trim();
    if (!answerToSubmit) {
      setErrorMessage('Please speak or type an answer before submitting.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    stopListening();

    try {
      // 1. Add candidate answer to transcript
      addTranscriptMessage('candidate', 'answer', answerToSubmit);

      // 2. Submit to backend
      const res: VoiceAnswerResponse = await api.submitVoiceAnswer(sessionId, currentIndex, answerToSubmit);
      if (res.status !== 'success') {
        throw new Error(res.message || 'Failed to evaluate answer.');
      }

      // 3. Add interviewer reaction to transcript
      addTranscriptMessage('interviewer', 'feedback', res.interviewer_reaction);

      // 4. Speak interviewer reaction aloud
      if (synthesisRef.current) {
        await synthesisRef.current.speak(res.interviewer_reaction);
      }

      setHasFollowup(res.has_adaptive_followup);
      setCandidateAnswer('');
      setInterimSpeech('');

      // If last question and no follow-up, conclude interview automatically
      if (res.is_last_question && !res.has_adaptive_followup) {
        await endInterview();
      }

      return res;
    } catch (err: any) {
      const msg = err.message || 'Error submitting answer.';
      setErrorMessage(msg);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, [addTranscriptMessage, candidateAnswer, currentIndex, endInterview, sessionId, stopListening]);

  /**
   * Requests an adaptive follow-up question.
   */
  const requestFollowup = useCallback(async () => {
    if (!sessionId) return;
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await api.getVoiceFollowup(sessionId, currentIndex);
      if (res.status !== 'success') {
        throw new Error(res.message || 'Failed to generate follow-up question.');
      }

      setFollowupData(res.follow_up);
      setHasFollowup(false); // Consumed

      // Add follow-up to transcript
      addTranscriptMessage('interviewer', 'followup', res.interviewer_speech);

      // Speak follow-up aloud
      if (synthesisRef.current) {
        await synthesisRef.current.speak(res.interviewer_speech);
      }

      // Restart listening for candidate response to follow-up
      if (!manualMode && recognitionRef.current) {
        await recognitionRef.current.startListening();
      }

      return res;
    } catch (err: any) {
      setErrorMessage(err.message || 'Error generating follow-up.');
    } finally {
      setIsSubmitting(false);
    }
  }, [addTranscriptMessage, currentIndex, manualMode, sessionId]);

  /**
   * Advances to next interview question.
   */
  const nextQuestion = useCallback(async () => {
    if (!sessionId) return;
    setErrorMessage(null);
    setCandidateAnswer('');
    setInterimSpeech('');
    setHasFollowup(false);
    setFollowupData(null);

    try {
      const res = await api.getVoiceQuestion(sessionId, 'next');
      if (res.status === 'completed') {
        await endInterview();
        return;
      }

      if (res.question) {
        setCurrentQuestion(res.question);
        setCurrentIndex(res.current_index || currentIndex + 1);

        if (res.interviewer_speech) {
          addTranscriptMessage('interviewer', 'question', res.interviewer_speech);
          if (synthesisRef.current) {
            await synthesisRef.current.speak(res.interviewer_speech);
          }
        }

        // Restart listening
        if (!manualMode && recognitionRef.current) {
          await recognitionRef.current.startListening();
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error retrieving next question.');
    }
  }, [addTranscriptMessage, currentIndex, endInterview, manualMode, sessionId]);


  return {
    // Session state
    sessionId,
    targetRole,
    difficulty,
    totalQuestions,
    currentIndex,
    currentQuestion,
    isCompleted,
    finalReport,

    // Audio & Transcription
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
    followupData,

    // Controls & Status
    errorMessage,
    isPermissionDenied,
    manualMode,
    privacyAccepted,
    capabilities,

    // Actions
    startInterview,
    toggleListening,
    startListening,
    stopListening,
    toggleMute,
    pauseSpeech,
    resumeSpeech,
    replayQuestion,
    updateCandidateAnswer,
    submitAnswer,
    requestFollowup,
    nextQuestion,
    endInterview,
    setManualMode,
    setPrivacyAccepted,
  };
}
