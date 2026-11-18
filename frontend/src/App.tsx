import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnalysisProvider } from './context/AnalysisContext';
import { Layout } from './components/layout/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { ResumeAnalyzerPage } from './pages/ResumeAnalyzerPage';
import { ResultsPage } from './pages/ResultsPage';
import { SkillGapPage } from './pages/SkillGapPage';
import { CareerMentorPage } from './pages/CareerMentorPage';
import { InterviewStudioPage } from './pages/InterviewStudioPage';
import { InterviewPracticePage } from './pages/InterviewPracticePage';
import { InterviewResultsPage } from './pages/InterviewResultsPage';
import { VoiceInterviewPage } from './pages/VoiceInterviewPage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { DatasetExplorerPage } from './pages/DatasetExplorerPage';

export function App() {
  return (
    <AnalysisProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/analyze" element={<ResumeAnalyzerPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/skill-gap" element={<SkillGapPage />} />
            <Route path="/career-mentor" element={<CareerMentorPage />} />
            <Route path="/interview-studio" element={<InterviewStudioPage />} />
            <Route path="/interview-practice" element={<InterviewPracticePage />} />
            <Route path="/interview-voice" element={<VoiceInterviewPage />} />
            <Route path="/interview-results" element={<InterviewResultsPage />} />
            <Route path="/model-performance" element={<ModelPerformancePage />} />
            <Route path="/datasets" element={<DatasetExplorerPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AnalysisProvider>
  );
}

export default App;
