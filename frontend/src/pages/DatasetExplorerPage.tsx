import React, { useState, useEffect } from 'react';
import {
  Database,
  ExternalLink,
  Layers,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  Sliders,
  BarChart2
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { api } from '../services/api';

export const DatasetExplorerPage: React.FC = () => {
  const [dataSummary, setDataSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDatasets()
      .then((res) => {
        if (res.summary) setDataSummary(res.summary);
      })
      .catch((err) => {
        console.warn('Dataset summary fetch warning:', err);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
          Dataset Explorer &amp; Preprocessing Statistics
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Provenance, schema validation, and linguistic properties of the verified public benchmarks.
        </p>
      </div>

      {/* Dataset Provenance Cards Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Primary Matching Dataset */}
        <Card
          title="Primary Matching Dataset"
          subtitle="Hugging Face research benchmark for compatibility"
          icon={Database}
          badge={<Badge variant="indigo" size="sm">7,999 Verified Pairs</Badge>}
          className="h-full"
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">
                cnamuangtoun/resume-job-description-fit
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Public research benchmark labeled for resume-to-job compatibility.
              </p>
            </div>

            <div className="space-y-2 text-xs divide-y divide-slate-800/80">
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Raw Source Records:</span>
                <span className="font-semibold text-slate-200">8,000 (6,241 Train / 1,759 Test)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Verified Records After Deduplication:</span>
                <span className="font-semibold text-emerald-400">7,999 (6,240 Train / 1,759 Test)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Duplicate Handling:</span>
                <span className="font-semibold text-slate-200">1 duplicate removed; raw source preserved</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Fields:</span>
                <code className="text-indigo-300 text-[11px]">resume_text, job_description_text, label</code>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Missing / Null Values:</span>
                <span className="font-semibold text-emerald-400">0 Null Values</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Unique Resumes:</span>
                <span className="font-semibold text-slate-200">642 in Train &bull; 477 in Test</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Unique Job Descriptions:</span>
                <span className="font-semibold text-emerald-400">280 in Train &bull; 71 in Test (0% Overlap)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Resume Overlap Across Source Splits:</span>
                <span className="font-semibold text-amber-400">476 / 477 Test Resumes (99.79%)</span>
              </div>
            </div>

            <div className="pt-2">
              <a
                href="https://huggingface.co/datasets/cnamuangtoun/resume-job-description-fit"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
              >
                <span>View on Hugging Face</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </Card>

        {/* Secondary Skills Dataset */}
        <Card
          title="Secondary Skills Dataset"
          subtitle="LinkedIn domain-extracted skills by RecAI"
          icon={FileSpreadsheet}
          badge={<Badge variant="emerald" size="sm">1,067 Records</Badge>}
          className="h-full"
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">
                batuhanmtl/job-skill-set
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Hugging Face dataset of LinkedIn job postings with domain-extracted skills by RecAI.
              </p>
            </div>

            <div className="space-y-2 text-xs divide-y divide-slate-800/80">
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Total Verified Postings:</span>
                <span className="font-semibold text-slate-200">1,067 Verified Job Profiles</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Unique Skills Extracted:</span>
                <span className="font-semibold text-emerald-400">4,476 Canonical Skill Lexicon</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Fields:</span>
                <code className="text-indigo-300 text-[11px]">job_id, category, job_title, job_skill_set</code>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Domain Categories:</span>
                <span className="font-semibold text-slate-200">Business-Dev, Finance, Sales, HR, IT</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Missing Values:</span>
                <span className="font-semibold text-emerald-400">0 Null Records</span>
              </div>
            </div>

            <div className="pt-2">
              <a
                href="https://huggingface.co/datasets/batuhanmtl/job-skill-set"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
              >
                <span>View on Hugging Face</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </Card>
      </div>

      {/* Visualizations Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Skills Distribution */}
        <Card
          title="Top 15 Extracted Skills Frequency"
          subtitle="Empirical frequency across verified benchmark records"
          icon={BarChart2}
        >
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-center">
            <img
              src="/images/top_skills_distribution.png"
              alt="Top Skills Distribution"
              className="w-full rounded-lg object-contain max-h-80 mx-auto"
            />
          </div>
        </Card>

        {/* Text Length Distributions */}
        <Card
          title="Document Length Characteristics"
          subtitle="Word count distributions for resumes and job postings"
          icon={Layers}
        >
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-center">
            <img
              src="/images/text_length_distributions.png"
              alt="Text Length Distribution"
              className="w-full rounded-lg object-contain max-h-80 mx-auto"
            />
          </div>
        </Card>
      </div>

      {/* Preprocessing Summary Visual */}
      <Card
        title="Preprocessing &amp; Experience Correlation Summary"
        subtitle="Feature transformation and experience alignment architecture"
        icon={Sliders}
      >
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-center">
          <img
            src="/images/preprocessing_summary.png"
            alt="Preprocessing Summary"
            className="w-full rounded-lg object-contain max-h-96 mx-auto"
          />
        </div>
      </Card>
    </div>
  );
};
