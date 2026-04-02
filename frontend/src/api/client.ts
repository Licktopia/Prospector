import type { Profile, Job, ScrapeResult, EvaluateResult } from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Profiles
export const getProfiles = () => request<Profile[]>('/profiles/');

export const getProfile = (id: number) => request<Profile>(`/profiles/${id}`);

export const scrapeJobs = (profileId: number) =>
  request<ScrapeResult>(`/profiles/${profileId}/scrape`, { method: 'POST' });

export const evaluateJobs = (profileId: number) =>
  request<EvaluateResult>(`/profiles/${profileId}/evaluate`, { method: 'POST' });

// Jobs
export const getJobs = (profileId: number, params?: Record<string, string>) => {
  const search = new URLSearchParams({ profile_id: String(profileId), ...params });
  return request<Job[]>(`/jobs/?${search}`);
};

export const getJob = (id: number) => request<Job>(`/jobs/${id}`);

export const updateJobStatus = (jobId: number, status: string) =>
  request<{ id: number; application_status: string }>(
    `/jobs/${jobId}/status?status=${status}`,
    { method: 'PATCH' }
  );

export const generateCoverLetter = (jobId: number, model: 'sonnet' | 'opus' = 'sonnet') =>
  request<{ id: number; cover_letter: string; model_used: string }>(
    `/jobs/${jobId}/generate-cover-letter?model=${model}`,
    { method: 'POST' }
  );
