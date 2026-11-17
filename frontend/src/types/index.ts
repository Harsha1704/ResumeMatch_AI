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

export interface CandidateName {
  preferred_name: string;
  full_name?: string | null;
  mentor_title: string;
  is_confident: boolean;
  extraction_method: string;
}

export interface CandidateContactInfo {
  emails: string[];
  primary_email: string;
  phones: string[];
  primary_phone: string;
  links: {
    linkedin?: string;
    github?: string;
    portfolio?: string;
    all_links: string[];
  };
}

export interface EducationRecord {
  degree_level: string;
  degree_name: string;
  field_of_study: string;
  institution: string;
  graduation_year?: number | null;
  gpa?: string | null;
  raw_text: string;
}

export interface CertificationRecord {
  title: string;
  issuer: string;
  year?: string | null;
  raw_text: string;
}

export interface CandidateProfile {
  name: CandidateName;
  contact_info: CandidateContactInfo;
  education: EducationRecord[];
  certifications: CertificationRecord[];
  duplicate_skills: Array<{ skill: string; sections: string[]; count: number }>;
  conflicts: Array<{ conflict_type: string; description: string }>;
  missing_fields: string[];
}

export interface EvidenceGroundedMatch {
  skill: string;
  tier: "Required" | "Preferred" | string;
  job_requirement_sentence: string;
  candidate_evidence: string;
  evidence_source: "project" | "internship" | "professional_experience" | "skills_section" | "candidate_confirmed" | "contradictory_claim" | "none" | string;
  match_classification: "fully_supported" | "partially_supported" | "explicitly_mentioned" | "missing_evidence" | "conflicting_evidence" | "candidate_confirmed" | string;
  confidence: number;
  explanation: string;
}

export interface MLCompatibilityScorecard {
  predicted_class: string;
  compatibility_score: number;
  model_confidence: number;
  probabilities: ClassProbabilities;
  model_used: string;
}

export interface SkillCoverageScorecard {
  full_coverage_pct: number;
  any_coverage_pct: number;
  matched_required_count: number;
  total_required_count: number;
  matched_preferred_count: number;
  total_preferred_count: number;
  fully_matched_required_count: number;
  partially_evidenced_required_count: number;
}

export interface ExperienceCoverageScorecard {
  job_required_years?: number | null;
  candidate_experience_years: number;
  meets_experience_requirement: boolean;
  has_full_time: boolean;
  has_internships: boolean;
  internships_count: number;
  has_projects: boolean;
  projects_count: number;
  primary_classification: string;
  display_summary: string;
}

export interface QualificationCoverageScorecard {
  detected_job_requirements: string[];
  candidate_degrees: string[];
  education_verified: boolean;
  verification_status?: "verified" | "unrelated_degree" | "missing_education" | "no_explicit_requirement" | "inconclusive" | string;
  notes: string;
}

export interface Scorecard {
  ml_compatibility: MLCompatibilityScorecard;
  skill_coverage: SkillCoverageScorecard;
  experience_coverage: ExperienceCoverageScorecard;
  qualification_coverage: QualificationCoverageScorecard;
}

export interface AnalysisResult {
  analysis_id: string;
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
  candidate_profile?: CandidateProfile;
  evidence_grounded_matches?: EvidenceGroundedMatch[];
  scorecard?: Scorecard;
  responsibilities?: string[];
  qualifications?: string[];
  tools_and_technologies?: string[];
  experience_requirements?: {
    min_years?: number | null;
    max_years?: number | null;
    context_sentence?: string;
    is_explicit?: boolean;
  };
}

export interface RoadmapMilestone {
  step_number: number;
  step_title: string;
  milestone_description: string;
  key_deliverable: string;
  estimated_hours: number;
  verification_method: string;
  task_key: string;
  completed?: boolean;
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

export interface CareerProfileIdentity {
  full_name: string;
  preferred_name: string;
  email?: string;
  has_email: boolean;
  phone?: string;
  has_phone: boolean;
  linkedin?: string;
  has_linkedin: boolean;
  github?: string;
  has_github: boolean;
  portfolio?: string;
  has_portfolio: boolean;
  location?: string;
}

export interface CareerProfileCompetency {
  skill: string;
  evidence_source: "project" | "internship" | "professional_experience" | "candidate_confirmed" | "skills_section" | string;
  provenance_title?: string;
  excerpt?: string;
  notes?: string;
  confidence: number;
}

export interface CareerProfileMissingInfo {
  field: string;
  category: string;
  impact: "High" | "Moderate" | "Low" | string;
  detail: string;
}

export interface CareerProfile {
  identity: CareerProfileIdentity;
  education: {
    records: EducationRecord[];
    total_degrees_count: number;
    education_verified: boolean;
    verification_status: string;
    notes: string;
  };
  certifications: CertificationRecord[];
  experience: {
    total_experience_years: number;
    full_time_years: number;
    internship_months: number;
    projects_count: number;
    internships_count: number;
    professional_roles_count: number;
    display_summary: string;
  };
  projects: Project[];
  internships: Internship[];
  demonstrated_competencies: CareerProfileCompetency[];
  candidate_confirmed_competencies: CareerProfileCompetency[];
  partially_evidenced_competencies: CareerProfileCompetency[];
  missing_or_uncertain_information: CareerProfileMissingInfo[];
  conflicts_and_inconsistencies: any[];
  evidence_metrics: {
    demonstrated_count: number;
    candidate_confirmed_count: number;
    partially_evidenced_count: number;
    missing_items_count: number;
    has_conflicts: boolean;
  };
}

export interface RecommendedRole {
  role_id: string;
  title: string;
  category: string;
  description: string;
  primary_focus: string;
  match_score: number;
  fit_tier: "Strong Fit" | "Potential Fit" | "Growth Fit" | string;
  fit_badge: "success" | "warning" | "info" | string;
  fit_reason: string;
  matching_skills: string[];
  matching_core_count: number;
  missing_core_skills: string[];
  missing_secondary_skills: string[];
  primary_gaps: string[];
  practical_next_action: string;
  market_intelligence_note: string;
}

export interface ResumeImprovementSuggestion {
  suggestion_id: string;
  category: string;
  priority: "High" | "Medium" | "Low" | string;
  reason: string;
  evidence_context: string;
  actionable_example: {
    before: string;
    after: string;
  };
  practical_next_action: string;
}

export interface CareerMilestone {
  milestone_id: string;
  phase: string;
  timeframe: string;
  title: string;
  goal: string;
  reason: string;
  supporting_evidence_or_gap: string;
  priority: "Critical" | "High" | "Medium" | string;
  deliverable: string;
  verification_criteria: string;
}

export interface CareerRoadmap {
  target_role: string;
  short_term: CareerMilestone[];
  medium_term: CareerMilestone[];
  total_milestones_count: number;
  guidance_philosophy: string;
}

export interface MentorDossier {
  [key: string]: any;
  candidate_preferred_name?: string;
  candidate_target_role?: string;
  candidate_education?: string;
  encouragement_message?: string;
  welcome_greeting?: string;
  target_role?: string;
  career_profile?: CareerProfile;
  recommended_roles?: RecommendedRole[];
  resume_improvement_suggestions?: ResumeImprovementSuggestion[];
  career_roadmap?: CareerRoadmap;
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
  related_skill?: string;
  reason_for_asking?: string;
  important_concepts?: string[];
  expected_key_points?: string[];
  expected_answer_evaluation_criteria?: string[];
  recommended_answer_framework?: "STAR" | "PAR" | "CAR" | "Direct Technical" | string;
  topic?: string;
  source_type?: string;
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
  completed_framework_answer?: Record<string, string>;
  evaluation?: HeuristicEvaluation;
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

export interface CriterionScore {
  score: number;
  weight_pct: number;
  status: string;
  details: string;
}

export interface HeuristicEvaluation {
  [key: string]: any;
  status: string;
  score: number;
  overall_score?: number;
  evaluator_label: string;
  disclaimer?: string;
  word_count?: number;
  completeness_level?: string;
  individual_criterion_scores?: Record<string, CriterionScore>;
  criterion_scores?: Record<string, CriterionScore>;
  framework_adherence: {
    framework: string;
    framework_id?: string;
    sections_addressed: string[];
    missing_sections?: string[];
    sections_missing?: string[];
    adherence_pct: number;
  };
  key_point_coverage: {
    covered?: string[];
    missing?: string[];
    points_covered?: string[];
    points_omitted?: string[];
    coverage_pct: number;
  };
  important_concepts_coverage?: {
    covered: string[];
    missing: string[];
    coverage_pct: number;
  };
  conceptual_depth?: {
    concepts_demonstrated: string[];
    depth_score: number;
  };
  evidence_detected?: boolean;
  strengths?: string[];
  areas_for_improvement?: string[];
  missing_concepts?: string[];
  improvement_suggestions?: string[];
  evidence_grounding_warnings?: string[];
  evidence_warnings?: string[];
  suggested_improved_answer_structure?: {
    framework_name: string;
    framework_id: string;
    recommended_steps: Array<{ step: string; guidance: string }>;
    safeguard_note: string;
  };
  actionable_feedback?: string;
  feedback_notes?: string[];
}

export interface InterviewSessionItem {
  session_id: string;
  owner_id?: string;
  analysis_id?: string;
  candidate_filename?: string;
  job_title?: string;
  target_role?: string;
  interview_mode?: string;
  difficulty?: string;
  is_completed: boolean;
  created_at: number;
  updated_at?: number;
  completed_at?: number;
  total_questions: number;
  answered_questions: number;
  results_summary?: Record<string, any>;
}

export interface InterviewProgressSummary {
  total_sessions: number;
  completed_sessions: number;
  total_questions_attempted: number;
  average_score: number;
  categories_practiced: Record<string, number>;
  struggled_topics: string[];
  recent_sessions: InterviewSessionItem[];
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
