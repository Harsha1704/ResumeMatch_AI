import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { AnalysisResult } from '../types';
import { api } from '../services/api';

interface AnalysisContextType {
  activeAnalysisId: string | null;
  currentAnalysis: AnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  modelBackend: 'production' | 'challenger_m5';
  setModelBackend: (backend: 'production' | 'challenger_m5') => void;
  setAnalysisResult: (result: AnalysisResult) => void;
  loadAnalysis: (id?: string) => Promise<AnalysisResult | null>;
  clearAnalysis: () => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(() => {
    return localStorage.getItem('rm_active_analysis_id') || 'sample-preview';
  });
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [modelBackend, setModelBackend] = useState<'production' | 'challenger_m5'>('production');

  const loadAnalysis = useCallback(async (id?: string): Promise<AnalysisResult | null> => {
    const targetId = id || activeAnalysisId || 'sample-preview';
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.getAnalysis(targetId);
      if (resp.status === 'success' && resp.analysis) {
        setCurrentAnalysis(resp.analysis);
        setActiveAnalysisId(resp.analysis.analysis_id);
        localStorage.setItem('rm_active_analysis_id', resp.analysis.analysis_id);
        return resp.analysis;
      }
      throw new Error('Analysis payload was not found.');
    } catch (err: any) {
      console.warn('Could not load analysis ID:', targetId, err.message);
      // Fallback to sample preview
      try {
        const sampleResp = await api.getAnalysis('sample');
        if (sampleResp.analysis) {
          setCurrentAnalysis(sampleResp.analysis);
          setActiveAnalysisId(sampleResp.analysis.analysis_id);
          localStorage.setItem('rm_active_analysis_id', sampleResp.analysis.analysis_id);
          return sampleResp.analysis;
        }
      } catch (fallbackErr: any) {
        setError(fallbackErr.message || 'Failed to initialize analysis preview.');
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [activeAnalysisId]);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  const setAnalysisResult = useCallback((result: AnalysisResult) => {
    setCurrentAnalysis(result);
    setActiveAnalysisId(result.analysis_id);
    localStorage.setItem('rm_active_analysis_id', result.analysis_id);
  }, []);

  const clearAnalysis = useCallback(() => {
    localStorage.removeItem('rm_active_analysis_id');
    setActiveAnalysisId('sample-preview');
    loadAnalysis('sample-preview');
  }, [loadAnalysis]);

  return (
    <AnalysisContext.Provider
      value={{
        activeAnalysisId,
        currentAnalysis,
        isLoading,
        error,
        modelBackend,
        setModelBackend,
        setAnalysisResult,
        loadAnalysis,
        clearAnalysis,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
};

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
}
