/**
 * TypeScript Types for Browser Voice Engine & Audio Controls (Phase 4).
 * Strict ₹0 Budget Architecture: Browser-Native SpeechRecognition and SpeechSynthesis.
 */

export type SpeechRecognitionStatus =
  | 'idle'
  | 'requesting_permission'
  | 'listening'
  | 'processing'
  | 'paused'
  | 'error'
  | 'unsupported';

export type SpeechSynthesisStatus =
  | 'idle'
  | 'speaking'
  | 'paused'
  | 'muted';

export interface BrowserSpeechCapabilities {
  speechRecognitionSupported: boolean;
  speechSynthesisSupported: boolean;
  recognitionEngine: 'SpeechRecognition' | 'webkitSpeechRecognition' | 'none';
  availableVoicesCount: number;
}

export interface VoiceTranscriptEntry {
  entry_id: string;
  session_id: string;
  speaker: 'interviewer' | 'candidate';
  message_type: 'greeting' | 'question' | 'answer' | 'feedback' | 'followup' | 'closing';
  message_text: string;
  timestamp: number;
  sequence_order: number;
  question_id?: string;
  answer_id?: string;
}

export interface VoiceStartPayload {
  analysis_id?: string;
  resume_text?: string;
  job_description?: string;
  target_role?: string;
  job_title?: string;
  difficulty?: string;
  interview_mode?: string;
  max_questions?: number;
}

export interface VoiceStartResponse {
  status: 'success' | 'error';
  session_id: string;
  target_role: string;
  difficulty: string;
  total_questions: number;
  current_index: number;
  current_question: any;
  interviewer_speech: string;
  provider: string;
  budget: string;
  message?: string;
}

export interface VoiceQuestionResponse {
  status: 'success' | 'completed' | 'error';
  session_id: string;
  current_index?: number;
  question_number?: number;
  total_questions?: number;
  question?: any;
  interviewer_speech?: string;
  message?: string;
}

export interface VoiceAnswerResponse {
  status: 'success' | 'error';
  session_id: string;
  question_index: number;
  evaluation: any;
  interviewer_reaction: string;
  has_adaptive_followup: boolean;
  is_last_question: boolean;
  message?: string;
}

export interface VoiceFollowupResponse {
  status: 'success' | 'error';
  session_id: string;
  question_index: number;
  follow_up: {
    question: string;
    reference_answer?: string;
    interview_takeaway?: string;
    practical_example?: string;
  };
  interviewer_speech: string;
  message?: string;
}

export interface VoiceEndResponse {
  status: 'success' | 'error';
  session_id: string;
  is_completed: boolean;
  results: any;
  final_report?: any;
  interviewer_speech: string;
  provider: string;
  budget: string;
  message?: string;
}

export interface VoiceHistoryItem {
  session_id: string;
  target_role: string;
  difficulty: string;
  interview_mode: string;
  created_at: number;
  completed_at?: number;
  is_completed: boolean;
  status: 'in_progress' | 'completed' | 'abandoned';
  total_questions: number;
  questions_answered: number;
  average_score?: number;
  summary_text?: string;
}

export interface VoiceSessionDetail {
  session: any;
  questions: any[];
  answers: any[];
  transcript: VoiceTranscriptEntry[];
  report?: any;
}
