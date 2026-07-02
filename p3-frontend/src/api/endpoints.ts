import { apiClient, ApiError } from "./client";
import type {
  UploadResponse,
  AnalyseResponse,
  Transaction,
  CaseSummary,
  CleanResponse,
} from "../types";
import {
  mockFetchCases,
  mockUploadStatement,
  mockFetchAnalysis,
  mockFetchTransactions,
  mockCleanStatement,
} from "../mocks/mockData";
import { setMockMode } from "../lib/mockMode";
import { shouldSkipBackend, markBackendOffline, markBackendOnline } from "./backendStatus";

function isNetworkError(err: unknown): boolean {
  return err instanceof ApiError && err.isNetworkError;
}

export async function uploadStatement(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockUploadStatement(file, onProgress);
  }

  try {
    const formData = new FormData();
    formData.append("file", file);

    const { data } = await apiClient.post<UploadResponse>("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      // Real statement processing can legitimately take longer than a plain
      // GET, so this call gets more room than the 8s default — but a dead
      // backend still fails via ECONNREFUSED almost immediately either way.
      timeout: 45000,
      onUploadProgress: (evt) => {
        if (onProgress && evt.total) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    });
    markBackendOnline();
    setMockMode(false);
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockUploadStatement(file, onProgress);
    }
    throw err;
  }
}

export async function fetchAnalysis(caseId: string): Promise<AnalyseResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockFetchAnalysis(caseId);
  }

  try {
    const { data } = await apiClient.get<AnalyseResponse>(`/analyse/${caseId}`);
    markBackendOnline();
    setMockMode(false);
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockFetchAnalysis(caseId);
    }
    throw err;
  }
}

export async function fetchTransactions(caseId: string): Promise<Transaction[]> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockFetchTransactions(caseId);
  }

  try {
    const { data } = await apiClient.get<Transaction[] | { transactions: Transaction[] }>(
      `/transactions/${caseId}`
    );
    markBackendOnline();
    setMockMode(false);
    return Array.isArray(data) ? data : data.transactions ?? [];
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockFetchTransactions(caseId);
    }
    throw err;
  }
}

export async function fetchCases(): Promise<CaseSummary[]> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockFetchCases();
  }

  try {
    const { data } = await apiClient.get<CaseSummary[] | { cases: CaseSummary[] }>("/cases");
    markBackendOnline();
    setMockMode(false);
    return Array.isArray(data) ? data : data.cases ?? [];
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockFetchCases();
    }
    throw err;
  }
}

export async function cleanStatement(file: File): Promise<CleanResponse> {
  if (shouldSkipBackend()) {
    setMockMode(true);
    return mockCleanStatement(file);
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await apiClient.post<CleanResponse>("/api/clean", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    markBackendOnline();
    setMockMode(false);
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      markBackendOffline();
      setMockMode(true);
      return mockCleanStatement(file);
    }
    throw err;
  }
}
