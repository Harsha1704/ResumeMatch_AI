export interface ClassProbabilities {
  "Good Fit": number;
  "Potential Fit": number;
  "No Fit": number;
  [key: string]: number;
}

export interface SkillGapSummary {
  total_required_count: number;
  matched_required_count: number;
  fully_matched_required_count: number;
  partially_evidenced_required_count: number;
  missing_required_count: number;
  total_preferred_count: number;
  matched_preferred_count: number;
  missing_preferred_count: number;
  total_resume_skills_count: number;
  full_coverage_pct: number;
  any_coverage_pct: number;
  full_coverage_display: string;
  any_coverage_display: string;
  coverage_status?: string;
}

export interface Project {
  title: string;
  technologies: string[];
  description: string;
  dates?: string;
  role?: string;
}

export interface Internship {
  organization: string;
  position: string;
  dates: string;
  technologies: string[];
  responsibilities: string[];
}

export interface EducationAnalysis {
  notes?: string;
  degrees?: string[];
  institutions?: string[];
  highest_degree?: string;
}

export interface ExperienceAnalysis {
  total_years_estimate?: number;
  meets_requirement?: boolean;
  required_years?: number;
  display_summary?: string;
  detected_projects?: Project[];
}

export interface Recommendation {
  category: string;
  action: string;
  rationale: string;
  severity: "danger" | "warning" | "info" | "success";
}

export interface LearningResource {
  skill: string;
  title: string;
  url: string;
  provider: string;
  level: string;
}

export interface AnalysisResult {
  analysis_id: string;
  is_demo?: boolean;
  filename?: string;
  job_title?: string;
  detected_job_title?: string;
  target_role_source?: string;
  predicted_class: "Good Fit" | "Potential Fit" | "No Fit" | string;
  model_confidence: number;
  compatibility_score: number;
  model_used: string;
  model_backend: string;
  is_challenger?: boolean;
  inference_latency_ms?: number;
  cache_status?: string;
  calibration_note?: string;
  class_probabilities: ClassProbabilities;
  skill_gap_summary: SkillGapSummary;
  projects?: Project[];
  internships?: Internship[];
  resume_skills: string[];
  matched_skills: string[];
  missing_skills: string[];
  required_skills: string[];
  preferred_skills: string[];
  matched_required_skills?: string[];
  fully_matched_required_skills?: string[];
  partially_evidenced_required_skills?: string[];
  missing_required_skills?: string[];
  matched_preferred_skills?: string[];
  missing_preferred_skills?: string[];
  education_analysis?: EducationAnalysis;
  experience_summary?: {
    total_years?: number;
    display_summary?: string;
  };
  experience_analysis?: ExperienceAnalysis;
  recommendations?: Recommendation[];
  learning_resources?: LearningResource[];
  job_description_text?: string;
  raw_jd?: string;
  pending_jobs?: {
    resume_job_id?: string;
    job_job_id?: string;
  };
  fallback_triggered?: boolean;
  fallback_reason?: string;
}

export interface RoadmapMilestone {
  step_number: number;
  step_title: string;
  task: string;
  deliverable?: string;
  exercise?: string;
  verification_method?: string;
  estimated_hours: number;
  task_key: string;
  status?: string;
  completed?: boolean;
  milestone_description?: string;
  key_deliverable?: string;
}

export interface Roadmap {
  skill_name: string;
  category: string;
  importance: string;
  total_estimated_hours: number;
  milestones: RoadmapMilestone[];
  needs_reinforcement?: boolean;
}

export interface CounselingAssessment {
  factor: string;
  status: string;
  detail: string;
}

export interface PrioritizedGap {
  skill_name: string;
  category: string;
  importance: "Mandatory Core" | "Preferred" | string;
  severity: "High" | "Medium" | "Low" | string;
  jd_frequency: number;
  rationale: string;
  counseling_profile?: CounselingAssessment[];
  learning_pathway?: {
    stage: string;
    action: string;
    target_metric: string;
  }[];
}

export interface MentorDossier {
  [key: string]: any;
  candidate_preferred_name?: string;
  candidate_target_role?: string;
  candidate_education?: string;
  encouragement_message?: string;
  welcome_greeting?: string;
  target_role?: string;
  identity?: {
    preferred_name?: string;
    mentor_title?: string;
    education?: string;
    [key: string]: any;
  };
  progress_summary?: {
    completed_tasks: number;
    total_tasks: number;
    completion_percentage?: number;
    percentage?: number;
    hours_invested?: number;
    total_hours_required?: number;
    disclaimer?: string;
    [key: string]: any;
  };
  strengths?: {
    total_skills?: number;
    verified_skills?: string[];
    projects_count?: number;
    internships_count?: number;
    projects?: Project[];
    internships?: Internship[];
    [key: string]: any;
  };
  gaps?: {
    top_priorities?: any[];
    expandable_requirements?: any[];
    total_gaps_count?: number;
    categories?: Record<string, any[]>;
    pathways?: any[];
    [key: string]: any;
  };
  roadmaps?: Roadmap[];
  timeline_days?: number;
  daily_hours?: number;
}

export interface InterviewQuestion {
  [key: string]: any;
  question_id: string;
  category: string;
  subcategory?: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced" | "Easy" | "Medium" | "Hard" | string;
  question_text: string;
  rationale?: string;
  important_concepts?: string[];
  expected_key_points?: string[];
  recommended_answer_framework?: "STAR" | "PAR" | "CAR" | "Direct Technical" | string;
  topic?: string;
  source_evidence?: string;
  user_answer?: string;
  question_number?: number;
  total_questions?: number;
  category_name?: string;
  category_badge?: string;
  source_reference?: string;
  detailed_answer?: string;
  simpler_answer?: string;
  short_answer?: string;
}

export interface InterviewEvidence {
  filename?: string;
  job_title?: string;
  total_skills?: number;
  matched_skills?: number;
  missing_skills?: number;
  projects_count?: number;
  internships_count?: number;
}

export interface HeuristicEvaluation {
  status: string;
  score: number;
  evaluator_label: string;
  framework_adherence: {
    framework: string;
    sections_addressed: string[];
    missing_sections: string[];
    adherence_pct: number;
  };
  key_point_coverage: {
    points_covered: string[];
    points_omitted: string[];
    coverage_pct: number;
  };
  conceptual_depth: {
    concepts_demonstrated: string[];
    depth_score: number;
  };
  feedback_notes: string[];
}

export interface ComparisonTableRow {
  model_name: string;
  artifact_id?: string;
  role: string;
  training_split?: string;
  evaluation_split?: string;
  accuracy: number;
  macro_f1: number;
  balanced_accuracy: number;
  good_fit_precision: number;
  good_fit_recall: number;
  latency_ms: string | number;
  memory_mb: string | number;
  verdict: string;
}

export interface ProtocolMetrics {
  accuracy: number;
  macro_f1: number;
  balanced_accuracy: number;
  good_fit_precision: number;
  good_fit_recall: number;
  confusion_matrix: number[][];
  roc_data?: { fpr: number[]; tpr: number[]; auc: number }[];
  pr_data?: { recall: number[]; precision: number[]; auc: number }[];
}

export interface ProtocolData {
  protocol_name: string;
  description: string;
  eval_samples: number;
  models: Record<string, {
    name: string;
    role: string;
    metrics: ProtocolMetrics;
  }>;
}

export interface ModelPerformanceData {
  classes: string[];
  comparison_table: ComparisonTableRow[];
  protocols: Record<string, ProtocolData>;
  default_protocol?: string;
  default_model?: string;
}

export interface DatasetPartitionSummary {
  split_name: string;
  total_pairs: number;
  unique_resumes: number;
  unique_jobs: number;
  class_balance: Record<string, number>;
  avg_resume_words: number;
  avg_job_words: number;
}

export interface DatasetSummary {
  dataset_name: string;
  total_pairs: number;
  verified_pairs: number;
  classes: Record<string, number>;
  partitions?: Record<string, DatasetPartitionSummary>;
  top_skills?: { skill: string; count: number }[];
  provenance_note?: string;
}
