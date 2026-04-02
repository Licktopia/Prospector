import { useState } from 'react';

interface CreateProfileModalProps {
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateProfileModal({ onClose, onCreated }: CreateProfileModalProps) {
  const [name, setName] = useState('');
  const [targetQueries, setTargetQueries] = useState('');
  const [targetLocations, setTargetLocations] = useState('');
  const [resume, setResume] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !resume || !targetQueries || !targetLocations) {
      setError('All fields are required');
      return;
    }

    setSubmitting(true);
    setError('');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('resume', resume);
    targetQueries.split('\n').filter(Boolean).forEach((q) => {
      formData.append('target_queries', q.trim());
    });
    targetLocations.split('\n').filter(Boolean).forEach((l) => {
      formData.append('target_locations', l.trim());
    });

    try {
      const res = await fetch('/api/profiles/', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      onCreated();
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">New Profile</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {error && (
            <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jane Smith"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resume (PDF)</label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setResume(e.target.files?.[0] ?? null)}
              className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Job Titles <span className="text-gray-400 font-normal">(one per line)</span>
            </label>
            <textarea
              value={targetQueries}
              onChange={(e) => setTargetQueries(e.target.value)}
              rows={4}
              placeholder={"Software Engineer\nData Scientist\nML Engineer"}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Locations <span className="text-gray-400 font-normal">(one per line)</span>
            </label>
            <textarea
              value={targetLocations}
              onChange={(e) => setTargetLocations(e.target.value)}
              rows={3}
              placeholder={"Remote\nDenver, CO\nNew York, NY"}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2 pb-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
