import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Database,
  Award,
  Target,
  BarChart2,
  FileSearch,
  Sparkles,
  GitBranch,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Layers,
  BookOpen
} from 'lucide-react';
import { MetricCard } from '../components/common/MetricCard';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { api } from '../services/api';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

export const DashboardPage: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api.getDashboard()
      .then((res) => {
        setDashboardData(res);
      })
      .catch((err) => {
        console.warn('Dashboard fetch warning:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const classData = [
    { name: 'No Fit (~50%)', value: 3999, color: '#EF4444' },
    { name: 'Potential Fit (~25%)', value: 2000, color: '#F59E0B' },
    { name: 'Good Fit (~25%)', value: 2000, color: '#10B981' },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-900 p-8 shadow-2xl">
        <div className="relative z-10 max-w-3xl">
          <Badge variant="indigo" size="md" className="mb-4">
            <ShieldCheck className="h-3.5 w-3.5" />
            SUPERVISED ML SYSTEM • ZERO LLM
          </Badge>
          <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            ResumeMatch AI
          </h2>
          <h3 className="mt-2 text-lg font-medium text-indigo-300">
            Multimodal Resume–Job Matching &amp; Skill Gap Analysis System
          </h3>
          <p className="mt-4 text-sm leading-relaxed text-slate-300">
            An end-to-end NLP and machine learning platform trained on 7,999 verified real-world resume-job pairs. Evaluates candidate fit, identifies critical skill gaps, and recommends actionable career enhancements without LLM dependencies.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 hover:scale-[1.02]"
            >
              <FileSearch className="h-4 w-4" />
              <span>Analyze a Resume</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/model-performance"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-700 hover:text-white"
            >
              <BarChart2 className="h-4 w-4 text-indigo-400" />
              <span>View ML Performance</span>
            </Link>
          </div>
        </div>

        {/* Ambient decorative backdrop */}
        <div className="pointer-events-none absolute -right-12 -top-12 h-96 w-96 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="pointer-events-none absolute right-12 bottom-0 hidden opacity-15 lg:block">
          <Cpu className="h-64 w-64 text-indigo-400" />
        </div>
      </div>

      {/* 4 Verified KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Verified Dataset"
          value="7,999"
          subtitle="6,240 train / 1,759 test pairs"
          icon={Database}
          accent="indigo"
          badge={<Badge variant="indigo" size="sm">Dual-Unseen</Badge>}
        />
        <MetricCard
          title="Selected Model"
          value="Logistic Reg."
          subtitle="Macro F1-selected baseline"
          icon={Award}
          accent="emerald"
          badge={<Badge variant="emerald" size="sm">Production</Badge>}
        />
        <MetricCard
          title="Held-Out Test Accuracy"
          value="50.43%"
          subtitle="71 Unseen Job Postings"
          icon={Target}
          accent="amber"
          badge={<Badge variant="amber" size="sm">Strict Isolation</Badge>}
        />
        <MetricCard
          title="Unseen Resumes F1"
          value="64.59%"
          subtitle="Group-Disjoint Validation"
          icon={BarChart2}
          accent="rose"
          badge={<Badge variant="rose" size="sm">Generalization</Badge>}
        />
      </div>

      {/* Main Grid: Class Distribution & 5-Step ML Workflow */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Class Distribution Visual */}
        <div className="lg:col-span-7">
          <Card
            title="Ground Truth Class Distribution"
            subtitle="Verified Partitions: Train (N=6,240) and Held-Out Test (N=1,759)"
            icon={Layers}
            badge={<Badge variant="slate" size="sm">cnamuangtoun Dataset</Badge>}
            className="h-full"
          >
            <div className="space-y-4">
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={classData}
                      cx="50%"
                      cy="50%"
                      innerRadius={65}
                      outerRadius={95}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {classData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0F172A',
                        borderColor: '#334155',
                        borderRadius: '0.5rem',
                        color: '#F8FAFC',
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-300">
                <div className="flex items-center gap-2 font-semibold text-slate-200">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Verified Partition Characteristics</span>
                </div>
                <p className="mt-1 leading-relaxed text-slate-400">
                  Labels are split into <strong className="text-rose-400">No Fit (~50%)</strong>,{' '}
                  <strong className="text-amber-400">Potential Fit (~25%)</strong>, and{' '}
                  <strong className="text-emerald-400">Good Fit (~25%)</strong>. The held-out test set contains 71 completely unseen job descriptions and unexposed candidate resumes.
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* System Architecture & Workflow */}
        <div className="lg:col-span-5">
          <Card
            title="Machine Learning Workflow"
            subtitle="Deterministic 5-Step Pipeline"
            icon={GitBranch}
            className="h-full"
          >
            <div className="space-y-4">
              {[
                {
                  step: 1,
                  title: 'Multi-Format Text Ingestion',
                  desc: 'PyMuPDF, python-docx, and TXT extractors preserve technical terms (C++, C#, .NET, Node.js).',
                  color: 'bg-indigo-500 text-white',
                },
                {
                  step: 2,
                  title: 'Feature Pipeline (2,518 Dims)',
                  desc: 'TF-IDF n-grams (1-2), cosine similarity, vector interaction, explicit experience gap, and structural features.',
                  color: 'bg-blue-500 text-white',
                },
                {
                  step: 3,
                  title: 'Supervised Compatibility Model',
                  desc: 'Logistic Regression predicts No Fit, Potential Fit, or Good Fit with genuine class probabilities.',
                  color: 'bg-emerald-500 text-white',
                },
                {
                  step: 4,
                  title: 'Deterministic Skill Gap Analysis',
                  desc: '4,476-skill taxonomy maps matched, missing mandatory, and partially evidenced skills.',
                  color: 'bg-amber-500 text-slate-900 font-bold',
                },
                {
                  step: 5,
                  title: 'Recommendations & Resources',
                  desc: 'Actionable resume improvement suggestions linked to verified official documentation.',
                  color: 'bg-purple-500 text-white',
                },
              ].map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-md ${item.color}`}
                  >
                    {item.step}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">{item.title}</h4>
                    <p className="mt-0.5 text-xs text-slate-400 leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="group rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6 shadow-lg transition-all duration-200 hover:border-indigo-500/50 hover:bg-slate-900">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:scale-110 transition-transform">
            <FileSearch className="h-6 w-6" />
          </div>
          <h4 className="mt-4 text-base font-bold text-slate-100">Resume Analyzer</h4>
          <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
            Upload your resume (PDF, DOCX, TXT) or paste text to test compatibility against any target job description.
          </p>
          <Link
            to="/analyze"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 group-hover:text-indigo-300"
          >
            <span>Launch Analyzer</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="group rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6 shadow-lg transition-all duration-200 hover:border-emerald-500/50 hover:bg-slate-900">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 group-hover:scale-110 transition-transform">
            <BarChart2 className="h-6 w-6" />
          </div>
          <h4 className="mt-4 text-base font-bold text-slate-100">Model Evaluation</h4>
          <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
            Inspect confusion matrices, ROC/PR curves, and multi-model benchmark results across validation splits.
          </p>
          <Link
            to="/model-performance"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 group-hover:text-emerald-300"
          >
            <span>View Metrics</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="group rounded-xl border border-slate-800 bg-[#0F172A]/80 p-6 shadow-lg transition-all duration-200 hover:border-blue-500/50 hover:bg-slate-900">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 group-hover:scale-110 transition-transform">
            <Database className="h-6 w-6" />
          </div>
          <h4 className="mt-4 text-base font-bold text-slate-100">Dataset Explorer</h4>
          <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
            Explore genuine data distributions, skill frequencies, document lengths, and partition provenance.
          </p>
          <Link
            to="/datasets"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-400 group-hover:text-blue-300"
          >
            <span>Explore Data</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
