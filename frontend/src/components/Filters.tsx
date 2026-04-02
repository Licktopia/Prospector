interface FiltersProps {
  status: string;
  minScore: string;
  searchQuery: string;
  searchQueries: string[];
  onStatusChange: (value: string) => void;
  onMinScoreChange: (value: string) => void;
  onSearchQueryChange: (value: string) => void;
}

const STATUSES = ['', 'new', 'evaluated', 'applied', 'rejected', 'interview'];

export default function Filters({
  status,
  minScore,
  searchQuery,
  searchQueries,
  onStatusChange,
  onMinScoreChange,
  onSearchQueryChange,
}: FiltersProps) {
  return (
    <div className="flex gap-4 items-end flex-wrap">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Status</label>
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Min Score</label>
        <input
          type="number"
          value={minScore}
          onChange={(e) => onMinScoreChange(e.target.value)}
          placeholder="0"
          min="0"
          max="100"
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-20"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Search Query</label>
        <select
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All queries</option>
          {searchQueries.map((q) => (
            <option key={q} value={q}>{q}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
