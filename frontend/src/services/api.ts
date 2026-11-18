import type {
  AnalysisResult,
  DatasetSummary,
  MentorDossier,
  InterviewQuestion,
  InterviewEvidence,
  ModelPerformanceData,
  HeuristicEvaluation
} from '../types';
import type {
  VoiceStartPayload,
  VoiceStartResponse,
  VoiceQuestionResponse,
  VoiceAnswerResponse,
  VoiceFollowupResponse,
  VoiceEndResponse,
  VoiceHistoryItem,
  VoiceSessionDetail
} from '../types/voice';

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '';

let cachedCsrfToken: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

export async function fetchCsrfToken(): Promise<string> {
  const fullUrl = `${API_BASE}/api/csrf-token`;
  try {
    const response = await fetch(fullUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!response.ok) return '';
    const data = await response.json();
    cachedCsrfToken = data?.csrf_token || '';
    return cachedCsrfToken || '';
  } catch {
    return '';
  }
}

export async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken) return cachedCsrfToken;
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) {
      cachedCsrfToken = decodeURIComponent(match[1]);
      return cachedCsrfToken;
    }
  }
  if (!csrfTokenPromise) {
    csrfTokenPromise = fetchCsrfToken().finally(() => {
      csrfTokenPromise = null;
    });
  }
  return csrfTokenPromise;
}

export function clearCsrfToken(): void {
  cachedCsrfToken = null;
  csrfTokenPromise = null;
}

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const method = (options.method || 'GET').toUpperCase();
  const isMutation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

  const defaultHeaders: Record<string, string> = {
    'Accept': 'application/json',
  };

  if (isMutation) {
    const csrf = await getCsrfToken();
    if (csrf) {
      defaultHeaders['X-CSRF-Token'] = csrf;
    }
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
    credentials: 'include',
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.error_message) errorDetail = errJson.error_message;
      else if (errJson.message) errorDetail = errJson.message;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  async getHealth() {
    return fetchJson<{
      status: string;
      model_loaded: boolean;
      challenger_available: boolean;
      active_backend_default: string;
      flask_rss_mb: number;
    }>('/health');
  },

  async getDashboard() {
    return fetchJson<{
      status: string;
      summary: Record<string, any>;
      dataset_summary: DatasetSummary;
      active_backend_default: string;
    }>('/api/dashboard');
  },

  async getSampleJobs() {
    return fetchJson<{
      status: string;
      sample_jobs: string[];
    }>('/api/sample-jobs');
  },

  async analyzeResume(formData: FormData): Promise<{ status: string; analysis_id: string; data: AnalysisResult }> {
    const fullUrl = `${API_BASE}/api/analyze`;
    const response = await fetch(fullUrl, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      let err = `Upload failed (${response.status})`;
      try {
        const j = await response.json();
        if (j.error_message) err = j.error_message;
      } catch {}
      throw new Error(err);
    }
    return response.json();
  },

  async analyzeJson(payload: {
    resume_text: string;
    job_description: string;
    target_role?: string;
    model_backend?: string;
  }): Promise<{ status: string; analysis_id: string; data: AnalysisResult }> {
    return fetchJson<{ status: string; analysis_id: string; data: AnalysisResult }>('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async getAnalysis(analysisId: string): Promise<{ status: string; analysis: AnalysisResult }> {
    return fetchJson<{ status: string; analysis: AnalysisResult }>(`/api/analysis/${encodeURIComponent(analysisId)}`);
  },

  async getSkillGap(analysisId?: string): Promise<{ status: string; analysis: AnalysisResult }> {
    const q = analysisId ? `?id=${encodeURIComponent(analysisId)}` : '';
    return fetchJson<{ status: string; analysis: AnalysisResult }>(`/api/skill-gap${q}`);
  },

  async getModelPerformance(): Promise<{ status: string; data: Record<string, any>; dashboard: ModelPerformanceData }> {
    return fetchJson<{ status: string; data: Record<string, any>; dashboard: ModelPerformanceData }>('/api/model-performance');
  },

  async getDatasets(): Promise<{ status: string; summary: DatasetSummary }> {
    return fetchJson<{ status: string; summary: DatasetSummary }>('/api/datasets');
  },

  async getCareerMentor(analysisId?: string, timelineDays = 14, dailyHours = 2.0): Promise<{ status: string; dossier: MentorDossier }> {
    const params = new URLSearchParams();
    if (analysisId) params.append('id', analysisId);
    params.append('timeline_days', timelineDays.toString());
    params.append('daily_hours', dailyHours.toString());
    return fetchJson<{ status: string; dossier: MentorDossier }>(`/api/career-mentor?${params.toString()}`);
  },

  async updateCandidateName(preferredName: string) {
    return fetchJson<{ status: string; preferred_name: string; mentor_title: string }>('/api/mentor/update-name', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferred_name: preferredName }),
    });
  },

  async updateCandidateRole(targetRole: string) {
    return fetchJson<{ status: string; target_role: string }>('/api/candidate/update-role', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_role: targetRole }),
    });
  },

  async confirmEducation(education: string) {
    return fetchJson<{ status: string; education: string }>('/api/candidate/confirm-education', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ education }),
    });
  },

  async updateMentorProgress(taskKey: string, status: string) {
    return fetchJson<{ status: string; task_key: string; current_status: string; progress_summary: any }>('/api/mentor/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_key: taskKey, status }),
    });
  },

  async resetMentorProgress() {
    return fetchJson<{ status: string; message: string }>('/api/mentor/reset-progress', {
      method: 'POST',
    });
  },

  async getInterviewStudio(analysisId?: string, category = 'ALL', difficulty = 'All', maxQuestions = 10): Promise<{
    status: string;
    evidence: InterviewEvidence;
    questions: InterviewQuestion[];
    technical_topics: string[];
    active_session_id?: string;
  }> {
    const params = new URLSearchParams();
    if (analysisId) params.append('id', analysisId);
    params.append('category', category);
    params.append('difficulty', difficulty);
    params.append('max_questions', maxQuestions.toString());
    return fetchJson(`/api/interview-studio?${params.toString()}`);
  },

  async generateInterviewQuestions(payload: {
    id?: string;
    category?: string;
    difficulty?: string;
    max_questions?: number;
    technical_topic?: string;
    framework?: string;
    action?: string;
    question_id?: string;
  }): Promise<{
    status: string;
    evidence: InterviewEvidence;
    questions: InterviewQuestion[];
    technical_topics: string[];
    active_session_id?: string;
  }> {
    return fetchJson('/api/interview-studio/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async getInterviewPractice(sessionId?: string): Promise<{
    status: string;
    session_id: string;
    question: InterviewQuestion;
    current_index: number;
    total_questions: number;
  }> {
    const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return fetchJson(`/api/interview-practice${q}`);
  },

  async submitPracticeAnswer(sessionId: string, questionIndex: number, userAnswer: string, direction = 'next'): Promise<{
    status: string;
    session_id: string;
    current_index: number;
    total_questions: number;
    is_finished: boolean;
  }> {
    return fetchJson('/api/interview-practice/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question_index: questionIndex,
        user_answer: userAnswer,
        direction,
      }),
    });
  },

  async getInterviewResults(sessionId?: string): Promise<{ status: string; results: any }> {
    const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return fetchJson(`/api/interview-results${q}`);
  },

  async evaluateAnswer(payload: {
    user_answer: string;
    question_text: string;
    expected_key_points?: string[];
    important_concepts?: string[];
    framework_id?: string;
    topic?: string;
  }): Promise<HeuristicEvaluation> {
    return fetchJson<HeuristicEvaluation>('/api/interview/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async confirmActivity(activityKey: string, confirmed: boolean) {
    return fetchJson<{ status: string; activity_key: string; confirmed: boolean }>('/api/interview/confirm-activity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activity_key: activityKey, confirmed }),
    });
  },

  async resetInterviewSession() {
    return fetchJson<{ status: string }>('/api/interview/reset', {
      method: 'POST',
    });
  },

  // =========================================================================
  // Voice Interview Room Endpoints
  // =========================================================================

  async startVoiceSession(payload: VoiceStartPayload): Promise<VoiceStartResponse> {
    return fetchJson<VoiceStartResponse>('/api/interview/voice/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async getVoiceQuestion(sessionId: string, direction = 'current'): Promise<VoiceQuestionResponse> {
    const params = new URLSearchParams({ session_id: sessionId, direction });
    return fetchJson<VoiceQuestionResponse>(`/api/interview/voice/question?${params.toString()}`);
  },

  async submitVoiceAnswer(sessionId: string, questionIndex: number, answerText: string): Promise<VoiceAnswerResponse> {
    return fetchJson<VoiceAnswerResponse>('/api/interview/voice/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question_index: questionIndex,
        answer_text: answerText,
      }),
    });
  },

  async getVoiceFollowup(sessionId: string, questionIndex: number): Promise<VoiceFollowupResponse> {
    return fetchJson<VoiceFollowupResponse>('/api/interview/voice/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question_index: questionIndex,
      }),
    });
  },

  async endVoiceSession(sessionId: string): Promise<VoiceEndResponse> {
    return fetchJson<VoiceEndResponse>('/api/interview/voice/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  async getVoiceHistory(limit = 50): Promise<{ status: string; history: VoiceHistoryItem[]; count: number }> {
    return fetchJson<{ status: string; history: VoiceHistoryItem[]; count: number }>(`/api/interview/voice/history?limit=${limit}`);
  },

  async getVoiceSessionDetail(sessionId: string): Promise<{ status: string; detail: VoiceSessionDetail }> {
    return fetchJson<{ status: string; detail: VoiceSessionDetail }>(`/api/interview/voice/history/${encodeURIComponent(sessionId)}`);
  },

  getExportUrl(type: string, protocol = 'job_disjoint_val', model = 'hybrid_config_d') {
    return `${API_BASE}/api/model-performance/export?type=${encodeURIComponent(type)}&protocol=${encodeURIComponent(protocol)}&model=${encodeURIComponent(model)}`;
  }
};
