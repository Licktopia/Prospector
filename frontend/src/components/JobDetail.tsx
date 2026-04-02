import { useState } from 'react';
import type { Job } from '../types';
import { updateJobStatus, generateCoverLetter } from '../api/client';
import ScoreBadge from './ScoreBadge';

interface JobDetailProps {
  job: Job;
  onStatusChange: (jobId: number, status: string) => void;
  onCoverLetterGenerated: (jobId: number, coverLetter: string) => void;
  onClose: () => void;
}

const STATUS_ACTIONS = ['applied', 'interview', 'rejected'] as const;

export default function JobDetail({ job, onStatusChange, onCoverLetterGenerated, onClose }: JobDetailProps) {
  const [copied, setCopied] = useState(false);
  const [updating, setUpdating] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selectedModel, setSelectedModel] = useState<'sonnet' | 'opus'>('sonnet');

  const handleStatusChange = async (status: string) => {
    setUpdating(status);
    try {
      await updateJobStatus(job.id, status);
      onStatusChange(job.id, status);
    } catch (err) {
      console.error('Failed to update status:', err);
    } finally {
      setUpdating(null);
    }
  };

  const handleCopy = async () => {
    if (job.cover_letter) {
      await navigator.clipboard.writeText(job.cover_letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await generateCoverLetter(job.id, selectedModel);
      onCoverLetterGenerated(job.id, result.cover_letter);
    } catch (err) {
      console.error('Failed to generate cover letter:', err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-white border-l border-gray-200">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0 mr-4">
            <h2 className="text-lg font-bold text-gray-900 truncate">{job.job_title}</h2>
            <p className="text-gray-600">{job.company_name}</p>
            <p className="text-sm text-gray-500">{job.location ?? 'Location not specified'}</p>
          </div>
          <div className="flex items-center gap-3">
            <ScoreBadge score={job.match_score} size="lg" />
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Status buttons */}
        <div className="flex gap-2 mt-3">
          {STATUS_ACTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleStatusChange(s)}
              disabled={updating !== null}
              className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
                job.application_status === s
                  ? s === 'applied' ? 'bg-green-600 text-white border-green-600'
                  : s === 'interview' ? 'bg-amber-600 text-white border-amber-600'
                  : 'bg-gray-600 text-white border-gray-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
              }`}
            >
              {updating === s ? '...' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
          {job.apply_links && job.apply_links.length > 0 ? (
            job.apply_links.map((link, i) => (
              <a
                key={i}
                href={link.link}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 first:ml-auto"
              >
                {link.title} &rarr;
              </a>
            ))
          ) : (
            <a
              href={job.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700"
            >
              View Original &rarr;
            </a>
          )}
        </div>
      </div>

      <div className="px-6 py-4 space-y-6">
        {/* Match Reasoning */}
        {job.match_reasoning && (
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Match Reasoning</h3>
            <p className="text-gray-700 leading-relaxed">{job.match_reasoning}</p>
          </section>
        )}

        {/* Cover Letter */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-900">Cover Letter</h3>
            <div className="flex items-center gap-2">
              {job.cover_letter && (
                <button
                  onClick={handleCopy}
                  className="px-3 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              )}
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as 'sonnet' | 'opus')}
                className="border border-gray-300 rounded text-xs px-2 py-1"
              >
                <option value="sonnet">Sonnet</option>
                <option value="opus">Opus</option>
              </select>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-3 py-1 rounded text-xs font-medium bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
              >
                {generating ? 'Generating...' : job.cover_letter ? 'Regenerate' : 'Generate'}
              </button>
            </div>
          </div>
          {job.cover_letter ? (
            <div className="text-gray-700 leading-relaxed whitespace-pre-wrap text-sm">
              {job.cover_letter}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">
              No cover letter yet. Click Generate to create one.
            </p>
          )}
        </section>

        {/* Job Description */}
        {job.job_description && (
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">Job Description</h3>
            <div className="text-gray-700 leading-relaxed whitespace-pre-wrap text-sm">
              {job.job_description}
            </div>
          </section>
        )}

        {/* Meta */}
        <section className="text-sm text-gray-500 space-y-1 pb-6">
          <div><span className="font-medium text-gray-700">Source:</span> {job.source ?? '--'}</div>
          <div><span className="font-medium text-gray-700">Search query:</span> {job.search_query ?? '--'}</div>
          <div><span className="font-medium text-gray-700">Added:</span> {new Date(job.date_added).toLocaleDateString()}</div>
          {job.date_evaluated && (
            <div><span className="font-medium text-gray-700">Evaluated:</span> {new Date(job.date_evaluated).toLocaleDateString()}</div>
          )}
        </section>
      </div>
    </div>
  );
}
