const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-50 text-blue-700',
  evaluated: 'bg-purple-50 text-purple-700',
  applied: 'bg-green-50 text-green-700',
  interview: 'bg-amber-50 text-amber-700',
  rejected: 'bg-gray-100 text-gray-600',
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const color = STATUS_COLORS[status] ?? 'bg-gray-50 text-gray-700';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}
