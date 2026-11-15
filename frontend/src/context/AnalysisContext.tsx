import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { AnalysisResult } from '../types';
import { api, ApiError } from '../services/api';

interface AnalysisContextType {
  activeAnalysisId: string | null;
  currentAnalysis: AnalysisResult | null;
  isDemo: boolean;
  isLoading: boolean;
  error: string | null;
  modelBackend: 'production' | 'challenger_m5';
  setModelBackend: (backend: 'production' | 'challenger_m5') => void;
  setAnalysisResult: (result: AnalysisResult) => void;
  loadAnalysis: (id?: string) => Promise<AnalysisResult | null>;
  loadDemoPreview: () => Promise<AnalysisResult | null>;
  retryLoad: () => Promise<AnalysisResult | null>;
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
    const isExplicitDemo = id === 'sample' || id === 'demo' || id === 'sample-preview';
    const targetId = id || activeAnalysisId || (localStorage.getItem('rm_active_analysis_id')) || 'sample-preview';

    setIsLoading(true);
    setError(null);

    try {
      const resp = await api.getAnalysis(targetId);
      if (resp.status === 'success' && resp.analysis) {
        setCurrentAnalysis(resp.analysis);
        setActiveAnalysisId(resp.analysis.analysis_id);
        if (!isExplicitDemo && resp.analysis.analysis_id !== 'sample-preview') {
          localStorage.setItem('rm_active_analysis_id', resp.analysis.analysis_id);
        }
        return resp.analysis;
      }
      throw new Error('Analysis payload was not found.');
    } catch (err: any) {
      console.warn('Could not load analysis ID:', targetId, err.message);

      const status = err instanceof ApiError ? err.status : undefined;
      const isAuthOrNotFound = status === 404 || status === 403;

      if (isAuthOrNotFound) {
        // Only treat 404 and 403 as expired or unauthorized IDs
        localStorage.removeItem('rm_active_analysis_id');
        setActiveAnalysisId(null);
        setError(`Analysis dossier was not found or is unauthorized (HTTP ${status || 'Error'}). Please upload a new resume or explore the demo preview.`);

        // If an explicit demo request failed, attempt clean sample recovery
        if (isExplicitDemo || targetId === 'sample-preview') {
          try {
            const sampleResp = await api.getAnalysis('sample');
            if (sampleResp.analysis) {
              setCurrentAnalysis(sampleResp.analysis);
              setActiveAnalysisId('sample-preview');
              return sampleResp.analysis;
            }
          } catch (fallbackErr: any) {
            setError(fallbackErr.message || 'Failed to initialize analysis preview.');
          }
        }
      } else {
        // Network failure, timeout, HTTP 500, or temporary outage
        // STRICT RULE: DO NOT clear localStorage and DO NOT switch user to demo data!
        setError(err.message || 'Network error or backend service temporarily unavailable. Please retry.');
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [activeAnalysisId]);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  const isDemo = Boolean(
    currentAnalysis?.is_demo ||
    activeAnalysisId === 'sample-preview' ||
    activeAnalysisId === 'sample' ||
    activeAnalysisId === 'demo'
  );

  const setAnalysisResult = useCallback((result: AnalysisResult) => {
    setCurrentAnalysis(result);
    setActiveAnalysisId(result.analysis_id);
    localStorage.setItem('rm_active_analysis_id', result.analysis_id);
    setError(null);
  }, []);

  const clearAnalysis = useCallback(() => {
    localStorage.removeItem('rm_active_analysis_id');
    setActiveAnalysisId('sample-preview');
    setError(null);
    loadAnalysis('sample-preview');
  }, [loadAnalysis]);

  const loadDemoPreview = useCallback(() => {
    return loadAnalysis('sample');
  }, [loadAnalysis]);

  const retryLoad = useCallback(() => {
    return loadAnalysis(activeAnalysisId || localStorage.getItem('rm_active_analysis_id') || undefined);
  }, [loadAnalysis, activeAnalysisId]);

  return (
    <AnalysisContext.Provider
      value={{
        activeAnalysisId,
        currentAnalysis,
        isDemo,
        isLoading,
        error,
        modelBackend,
        setModelBackend,
        setAnalysisResult,
        loadAnalysis,
        loadDemoPreview,
        retryLoad,
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
