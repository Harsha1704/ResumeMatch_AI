import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  Trash2,
  Briefcase,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Zap,
  ShieldCheck,
  X
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { useAnalysis } from '../context/AnalysisContext';
import { api } from '../services/api';

export const ResumeAnalyzerPage: React.FC = () => {
  const navigate = useNavigate();
  const { setAnalysisResult, modelBackend, setModelBackend } = useAnalysis();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pastedResumeText, setPastedResumeText] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [sampleJobs, setSampleJobs] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getSampleJobs()
      .then((res) => {
        if (res.sample_jobs && res.sample_jobs.length > 0) {
          setSampleJobs(res.sample_jobs);
        }
      })
      .catch((err) => {
        console.warn('Could not load sample jobs:', err);
      });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 16 * 1024 * 1024) {
        setErrorMessage('File exceeds maximum size of 16 MB.');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validExts = ['.pdf', '.docx', '.txt'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!validExts.includes(fileExt)) {
        setErrorMessage('Invalid file type. Please upload a PDF, DOCX, or TXT resume.');
        return;
      }
      if (file.size > 16 * 1024 * 1024) {
        setErrorMessage('File exceeds maximum size of 16 MB.');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedFile && !pastedResumeText.trim()) {
      setErrorMessage('Please upload a resume file (PDF, DOCX, TXT) or paste resume text.');
      return;
    }

    if (!jobDescription.trim()) {
      setErrorMessage('Target job description is required.');
      return;
    }

    setIsSubmitting(true);

    try {
      let result;
      if (selectedFile) {
        const formData = new FormData();
        formData.append('resume_file', selectedFile);
        formData.append('job_description', jobDescription);
        if (targetRole.trim()) {
          formData.append('target_role', targetRole.trim());
        }
        formData.append('model_backend', modelBackend);

        const res = await api.analyzeResume(formData);
        result = res.data;
      } else {
        const res = await api.analyzeJson({
          resume_text: pastedResumeText.trim(),
          job_description: jobDescription.trim(),
          target_role: targetRole.trim() || undefined,
          model_backend: modelBackend,
        });
        result = res.data;
      }

      setAnalysisResult(result);
      navigate(`/results?id=${encodeURIComponent(result.analysis_id)}`);
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during analysis.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
          Resume &amp; Job Description Compatibility Analyzer
        </h2>
        <p className="mt-1.5 text-sm text-slate-400">
          Upload a student resume and specify a target job description to evaluate supervised compatibility, extract skill gaps, and receive learning roadmaps.
        </p>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400" />
          <span className="flex-1 font-medium">{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Panel: Resume Input */}
          <Card
            title="1. Student Resume"
            subtitle="Drop resume file or paste raw plain text"
            icon={FileText}
            badge={<Badge variant="indigo" size="sm">PDF, DOCX, TXT</Badge>}
            className="flex flex-col"
          >
            {/* Drag & Drop Zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3">
                <UploadCloud className="h-7 w-7" />
              </div>
              <h4 className="text-sm font-bold text-slate-200">
                Drag &amp; Drop Resume File Here
              </h4>
              <p className="mt-1 text-xs text-slate-400">
                Supports PDF, DOCX, or plain text (Max 16 MB)
              </p>
              <button
                type="button"
                className="mt-4 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white"
              >
                Browse Files
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
              />
            </div>

            {/* Selected File Card */}
            {selectedFile && (
              <div className="mt-4 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5">
                <div className="flex items-center gap-3 truncate">
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                  <div className="truncate">
                    <p className="truncate text-xs font-bold text-slate-200">
                      {selectedFile.name}
                    </p>
                    <p className="text-[11px] text-slate-400">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400"
                  title="Remove file"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Or Paste Text Fallback */}
            <div className="mt-6 pt-4 border-t border-slate-800/80">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Or Paste Resume Content Directly:
              </label>
              <textarea
                rows={5}
                value={pastedResumeText}
                onChange={(e) => setPastedResumeText(e.target.value)}
                placeholder="Paste full raw text here if you prefer not uploading a file..."
                className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </Card>

          {/* Right Panel: Target Job Description */}
          <Card
            title="2. Target Job Description"
            subtitle="Paste target job posting & role title"
            icon={Briefcase}
            actions={
              <div className="flex items-center gap-2">
                <Badge variant="slate" size="sm">
                  {jobDescription.length} chars
                </Badge>
                {jobDescription && (
                  <button
                    type="button"
                    onClick={() => setJobDescription('')}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Clear
                  </button>
                )}
              </div>
            }
            className="flex flex-col"
          >
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Target Role (Optional)
              </label>
              <input
                type="text"
                maxLength={120}
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g., Machine Learning Engineer"
                className="w-full rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <p className="mt-1 text-[11px] text-slate-500">
                Use this to clarify the role title. Skill requirements and ML scoring still come from the job description below.
              </p>
            </div>

            <div className="mt-4 flex-1">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Job Posting Text (Required)
              </label>
              <textarea
                rows={8}
                required
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste target job posting including required skills, qualifications, responsibilities, and experience prerequisites..."
                className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Quick Test Samples */}
            {sampleJobs.length > 0 && (
              <div className="mt-4 rounded-xl border border-slate-800/80 bg-slate-900/40 p-3.5">
                <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-400 mb-2">
                  <Zap className="h-3.5 w-3.5" />
                  Quick Test with Real Dataset Job Description:
                </span>
                <div className="flex flex-wrap gap-2">
                  {sampleJobs.map((sample, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setJobDescription(sample)}
                      className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white"
                    >
                      Sample Position #{idx + 1}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Inference Engine Architecture Selection */}
        <Card
          title="Inference Engine Architecture Selection"
          subtitle="Choose between production baseline and experimental challenger"
          icon={Cpu}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label
              className={`flex items-start gap-3 rounded-xl border p-4 cursor-pointer transition-all ${
                modelBackend === 'production'
                  ? 'border-emerald-500/50 bg-emerald-500/10'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <input
                type="radio"
                name="model_backend"
                value="production"
                checked={modelBackend === 'production'}
                onChange={() => setModelBackend('production')}
                className="mt-1 text-indigo-600 focus:ring-indigo-500"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">Production Baseline</span>
                  <Badge variant="emerald" size="sm">Default / Stable</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                  Trained TF-IDF + Logistic Regression baseline. Lean CPU memory footprint (&lt; 200 MB RSS) with zero transformer overhead.
                </p>
              </div>
            </label>

            <label
              className={`flex items-start gap-3 rounded-xl border p-4 cursor-pointer transition-all ${
                modelBackend === 'challenger_m5'
                  ? 'border-amber-500/50 bg-amber-500/10'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <input
                type="radio"
                name="model_backend"
                value="challenger_m5"
                checked={modelBackend === 'challenger_m5'}
                onChange={() => setModelBackend('challenger_m5')}
                className="mt-1 text-indigo-600 focus:ring-indigo-500"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">Challenger Model 5</span>
                  <Badge variant="amber" size="sm">Experimental</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                  Semantic SBERT + 28-dim Skill Fusion with persistent SQLite embedding cache. +78.6% Good Fit recall improvement.
                </p>
              </div>
            </label>
          </div>
        </Card>

        {/* Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#0F172A]/90 p-4 shadow-lg">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Private processing • Resumes are parsed in memory and never shared publicly.</span>
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Running Deterministic Matcher...</span>
              </>
            ) : (
              <>
                <Cpu className="h-4 w-4" />
                <span>Run Compatibility &amp; Skill Gap Analysis</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
