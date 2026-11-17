import type {
  AnalysisResult,
  DatasetSummary,
  MentorDossier,
  InterviewQuestion,
  InterviewEvidence,
  ModelPerformanceData,
  HeuristicEvaluation
} from '../types';

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '';

let cachedCsrfToken: string | null = null;
let csrfTokenPromise: Promise<string> | null = null;

export async function fetchCsrfToken(): Promise<string> {
  const fullUrl = `${API_BASE}/api/csrf-token`;
  const response = await fetch(fullUrl, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to retrieve CSRF token: HTTP ${response.status}`);
  }

  const data = await response.json();
  if (!data?.csrf_token) {
    throw new Error('CSRF endpoint returned invalid response');
  }

  cachedCsrfToken = data.csrf_token;
  return data.csrf_token;
}

export async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }
  // Fallback to cookie or meta tag if present
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) {
      cachedCsrfToken = decodeURIComponent(match[1]);
      return cachedCsrfToken;
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) {
      cachedCsrfToken = meta.getAttribute('content')!;
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
    // Fail-closed: Must obtain a valid CSRF token before performing any mutation.
    const csrf = await getCsrfToken();
    if (!csrf || typeof csrf !== 'string' || csrf.trim() === '') {
      throw new Error('CSRF token could not be established. Mutation aborted.');
    }
    defaultHeaders['X-CSRF-Token'] = csrf;
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
    credentials: 'include', // send cookies cross-origin for session ownership & CSRF
  });

  if (!response.ok) {
    if (response.status === 403) {
      clearCsrfToken();
      let errorDetail = 'Security check failed: session expired or CSRF token invalid. Please refresh.';
      try {
        const errJson = await response.json();
        if (errJson.message) errorDetail = errJson.message;
        else if (errJson.error_message) errorDetail = errJson.error_message;
      } catch {
        // ignore
      }
      throw new Error(errorDetail);
    }
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
    // Fail-closed: Abort upload before fetch if CSRF token cannot be established
    const csrf = await getCsrfToken();
    if (!csrf || typeof csrf !== 'string' || csrf.trim() === '') {
      throw new Error('CSRF token could not be established. Resume upload aborted.');
    }
    const response = await fetch(fullUrl, {
      method: 'POST',
      body: formData,
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'X-CSRF-Token': csrf,
      },
    });
    if (!response.ok) {
      if (response.status === 403) {
        clearCsrfToken();
        let errorDetail = 'Security check failed: session expired or CSRF token invalid. Please refresh.';
        try {
          const errJson = await response.json();
          if (errJson.message) errorDetail = errJson.message;
          else if (errJson.error_message) errorDetail = errJson.error_message;
        } catch {
          // ignore
        }
        throw new Error(errorDetail);
      }
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

  async evaluateRole(roleName: string, analysisId?: string) {
    return fetchJson<{ status: string; role_evaluation: any }>('/api/career-mentor/evaluate-role', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role_name: roleName, analysis_id: analysisId }),
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

  async getInterviewStudio(
    analysisId?: string,
    category = 'ALL',
    difficulty = 'All',
    maxQuestions = 10,
    mode = 'mixed',
    targetRole?: string
  ): Promise<{
    status: string;
    evidence: InterviewEvidence;
    questions: InterviewQuestion[];
    technical_topics: string[];
    active_session_id?: string;
    recent_sessions?: any[];
  }> {
    const params = new URLSearchParams();
    if (analysisId) params.append('id', analysisId);
    params.append('category', category);
    params.append('difficulty', difficulty);
    params.append('max_questions', maxQuestions.toString());
    if (mode) params.append('mode', mode);
    if (targetRole) params.append('target_role', targetRole);
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
    mode?: string;
    target_role?: string;
    csrf_token?: string;
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

  async createInterviewSession(payload: {
    analysis_id?: string;
    mode?: string;
    difficulty?: string;
    max_questions?: number;
    target_role?: string;
    category?: string;
    csrf_token?: string;
  }): Promise<{
    status: string;
    session: any;
    question: InterviewQuestion;
  }> {
    return fetchJson('/api/interview/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async getInterviewSessions(analysisId?: string): Promise<{
    status: string;
    sessions: any[];
  }> {
    const q = analysisId ? `?analysis_id=${encodeURIComponent(analysisId)}` : '';
    return fetchJson(`/api/interview/sessions${q}`);
  },

  async getInterviewSessionDetail(sessionId: string): Promise<{
    status: string;
    session: any;
  }> {
    return fetchJson(`/api/interview/sessions/${encodeURIComponent(sessionId)}`);
  },

  async deleteInterviewSession(sessionId: string, csrfToken?: string): Promise<{
    status: string;
    message: string;
    session_id: string;
  }> {
    return fetchJson(`/api/interview/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
    });
  },

  async getInterviewProgress(analysisId?: string): Promise<{
    status: string;
    progress: any;
  }> {
    const q = analysisId ? `?analysis_id=${encodeURIComponent(analysisId)}` : '';
    return fetchJson(`/api/interview/progress${q}`);
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

  getExportUrl(type: string, protocol = 'job_disjoint_val', model = 'hybrid_config_d') {
    return `${API_BASE}/api/model-performance/export?type=${encodeURIComponent(type)}&protocol=${encodeURIComponent(protocol)}&model=${encodeURIComponent(model)}`;
  }
};
