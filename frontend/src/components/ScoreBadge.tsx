interface ScoreBadgeProps {
  score: number | null;
  size?: 'sm' | 'lg';
}

export default function ScoreBadge({ score, size = 'sm' }: ScoreBadgeProps) {
  if (score === null) return <span className="text-gray-400">--</span>;

  const color =
    score >= 75 ? 'bg-green-100 text-green-800' :
    score >= 50 ? 'bg-yellow-100 text-yellow-800' :
    'bg-red-100 text-red-800';

  const sizeClass = size === 'lg'
    ? 'text-2xl font-bold px-3 py-1'
    : 'text-xs font-semibold px-2 py-0.5';

  return (
    <span className={`inline-block rounded-full ${color} ${sizeClass}`}>
      {score}
    </span>
  );
}
