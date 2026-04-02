import { useEffect, useState, useCallback } from 'react';
import type { Profile, Job } from './types';
import { getProfiles, getJobs, getJob, scrapeJobs, evaluateJobs } from './api/client';
import JobTable from './components/JobTable';
import JobDetail from './components/JobDetail';
import Filters from './components/Filters';
import CreateProfileModal from './components/CreateProfileModal';

export default function App() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [currentProfileId, setCurrentProfileId] = useState<number | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [showCreateProfile, setShowCreateProfile] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterMinScore, setFilterMinScore] = useState('');
  const [filterSearchQuery, setFilterSearchQuery] = useState('');

  // Load profiles on mount
  useEffect(() => {
    getProfiles().then((p) => {
      setProfiles(p);
      if (p.length > 0) setCurrentProfileId(p[0].id);
      setLoading(false);
    });
  }, []);

  // Load jobs when profile or filters change
  const loadJobs = useCallback(async () => {
    if (!currentProfileId) return;
    setLoading(true);
    const params: Record<string, string> = {};
    if (filterStatus) params.status = filterStatus;
    if (filterMinScore) params.min_score = filterMinScore;
    if (filterSearchQuery) params.search_query = filterSearchQuery;
    const data = await getJobs(currentProfileId, params);
    setJobs(data);
    setLoading(false);
  }, [currentProfileId, filterStatus, filterMinScore, filterSearchQuery]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Update selected job when jobs list refreshes (e.g. after scrape/evaluate),
  // but only sync status from the list — don't overwrite full detail fields.
  useEffect(() => {
    if (selectedJob) {
      const updated = jobs.find((j) => j.id === selectedJob.id);
      if (updated && updated.application_status !== selectedJob.application_status) {
        setSelectedJob((prev) => prev ? { ...prev, application_status: updated.application_status } : null);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs]);

  const handleScrape = async () => {
    if (!currentProfileId) return;
    setActionLoading('scrape');
    try {
      const result = await scrapeJobs(currentProfileId);
      alert(`Scrape complete: ${result.new_inserted} new jobs found, ${result.skipped} skipped`);
      await loadJobs();
    } catch (err) {
      alert('Scrape failed: ' + (err as Error).message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEvaluate = async () => {
    if (!currentProfileId) return;
    setActionLoading('evaluate');
    try {
      const result = await evaluateJobs(currentProfileId);
      alert(`Evaluation complete: ${result.jobs_evaluated} jobs scored, avg ${result.avg_score}`);
      await loadJobs();
    } catch (err) {
      alert('Evaluation failed: ' + (err as Error).message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSelectJob = async (job: Job) => {
    setSelectedJob(job); // Show immediately with list data
    const full = await getJob(job.id); // Then fetch full details
    setSelectedJob(full);
  };

  const handleStatusChange = (jobId: number, status: string) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, application_status: status } : j))
    );
    if (selectedJob?.id === jobId) {
      setSelectedJob((prev) => prev ? { ...prev, application_status: status } : null);
    }
  };

  const handleCoverLetterGenerated = (jobId: number, coverLetter: string) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, cover_letter: coverLetter } : j))
    );
    if (selectedJob?.id === jobId) {
      setSelectedJob((prev) => prev ? { ...prev, cover_letter: coverLetter } : null);
    }
  };

  // Unique search queries for filter dropdown
  const searchQueries = [...new Set(jobs.map((j) => j.search_query).filter(Boolean))] as string[];

  const currentProfile = profiles.find((p) => p.id === currentProfileId);
  const scoredJobs = jobs.filter((j) => j.match_score !== null);
  const avgScore = scoredJobs.length
    ? (scoredJobs.reduce((sum, j) => sum + j.match_score!, 0) / scoredJobs.length).toFixed(0)
    : '0';

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
        <div className="max-w-full flex items-center justify-between">
          <span className="text-xl font-bold text-gray-900">Prospector</span>
          <div className="flex items-center gap-4">
            {profiles.length > 0 && (
              <select
                value={currentProfileId ?? ''}
                onChange={(e) => {
                  setCurrentProfileId(Number(e.target.value));
                  setSelectedJob(null);
                }}
                className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
              >
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            )}
            <button
              onClick={() => setShowCreateProfile(true)}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              + New Profile
            </button>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Table */}
        <div className={`flex flex-col overflow-hidden transition-all ${selectedJob ? 'w-1/2' : 'w-full'}`}>
          <div className="px-6 py-4 flex-shrink-0">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {currentProfile?.name ?? 'No profile'}
                </h1>
                <p className="text-sm text-gray-500">
                  {jobs.length} jobs {scoredJobs.length > 0 && `· avg score ${avgScore}`}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleScrape}
                  disabled={actionLoading !== null}
                  className="bg-green-600 text-white px-4 py-2 rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === 'scrape' ? 'Scraping...' : 'Run Scraper'}
                </button>
                <button
                  onClick={handleEvaluate}
                  disabled={actionLoading !== null}
                  className="bg-purple-600 text-white px-4 py-2 rounded-md text-sm hover:bg-purple-700 disabled:opacity-50"
                >
                  {actionLoading === 'evaluate' ? 'Evaluating...' : 'Run Evaluator'}
                </button>
              </div>
            </div>

            {/* Filters */}
            <Filters
              status={filterStatus}
              minScore={filterMinScore}
              searchQuery={filterSearchQuery}
              searchQueries={searchQueries}
              onStatusChange={setFilterStatus}
              onMinScoreChange={setFilterMinScore}
              onSearchQueryChange={setFilterSearchQuery}
            />
          </div>

          {/* Table */}
          <div className="flex-1 overflow-y-auto px-6 pb-6">
            {loading ? (
              <div className="text-center py-12 text-gray-500">Loading...</div>
            ) : (
              <JobTable
                jobs={jobs}
                onSelectJob={handleSelectJob}
                selectedJobId={selectedJob?.id}
              />
            )}
          </div>
        </div>

        {/* Right: Detail panel */}
        {selectedJob && (
          <div className="w-1/2 flex-shrink-0">
            <JobDetail
              key={selectedJob.id}
              job={selectedJob}
              onStatusChange={handleStatusChange}
              onCoverLetterGenerated={handleCoverLetterGenerated}
              onClose={() => setSelectedJob(null)}
            />
          </div>
        )}
      </div>
      {showCreateProfile && (
        <CreateProfileModal
          onClose={() => setShowCreateProfile(false)}
          onCreated={() => {
            getProfiles().then((p) => {
              setProfiles(p);
              if (p.length > 0) setCurrentProfileId(p[p.length - 1].id);
            });
          }}
        />
      )}
    </div>
  );
}
