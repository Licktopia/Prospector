import type { Job } from '../types';
import ScoreBadge from './ScoreBadge';
import StatusBadge from './StatusBadge';

interface JobTableProps {
  jobs: Job[];
  onSelectJob: (job: Job) => void;
  selectedJobId?: number;
}

export default function JobTable({ jobs, onSelectJob, selectedJobId }: JobTableProps) {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No jobs match your filters.</p>
        <p className="text-sm mt-1">Try running the scraper or adjusting your filters.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Title</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Company</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Location</th>
            <th className="text-center px-4 py-3 font-medium text-gray-600">Score</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs.map((job) => (
            <tr
              key={job.id}
              onClick={() => onSelectJob(job)}
              className={`cursor-pointer transition-colors ${
                selectedJobId === job.id
                  ? 'bg-blue-50'
                  : 'hover:bg-gray-50'
              }`}
            >
              <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">
                {job.job_title}
              </td>
              <td className="px-4 py-3 text-gray-600">{job.company_name}</td>
              <td className="px-4 py-3 text-gray-500">{job.location ?? '--'}</td>
              <td className="px-4 py-3 text-center">
                <ScoreBadge score={job.match_score} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={job.application_status} />
              </td>
              <td className="px-4 py-3 text-gray-500">
                {new Date(job.date_added).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
