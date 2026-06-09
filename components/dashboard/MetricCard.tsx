import type { MetricCardProps } from '@/types/dashboard';

const colorClasses = {
  green: { value: 'text-accent-green', bar: 'bg-accent-green' },
  blue:  { value: 'text-accent-blue',  bar: 'bg-accent-blue'  },
  coral: { value: 'text-accent-coral', bar: 'bg-accent-coral' },
  default: { value: 'text-text-primary', bar: 'bg-text-primary' },
} as const;

function isValueMissing(value: MetricCardProps['value']): boolean {
  return value === null || value === undefined;
}

function formatMetricValue(value: number | string): string {
  return typeof value === 'number' ? value.toLocaleString() : value;
}

/**
 * Displays a single health metric with an optional progress bar.
 * Value text uses `font-mono-display` (JetBrains Mono) and is tinted
 * with one of the Midnight Terminal accent tokens.
 */
export function MetricCard({
  label,
  value,
  unit,
  color = 'default',
  progress,
  barColor,
}: MetricCardProps) {
  const { value: valueClass, bar: barClass } = colorClasses[color];
  const missing = isValueMissing(value);
  const percentage =
    progress && progress.goal > 0 && progress.current != null
      ? Math.min(Math.round((progress.current / progress.goal) * 100), 100)
      : 0;

  return (
    <div>
      <p className="text-sm text-text-secondary mb-1">{label}</p>

      <div className="flex items-baseline gap-2">
        {missing ? (
          <span className="text-2xl font-mono-display text-text-secondary">—</span>
        ) : (
          <span className={`text-2xl font-mono-display ${valueClass}`}>
            {formatMetricValue(value)}
          </span>
        )}
        {unit && <span className="text-sm text-text-secondary">{unit}</span>}
      </div>

      {progress && (
        <div className="mt-2">
          <div className="h-1 bg-background-hover rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${barColor ? '' : barClass}`}
              style={{ width: `${percentage}%`, ...(barColor && { backgroundColor: barColor }) }}
            />
          </div>
          <p className="mt-1 text-xs text-text-secondary font-mono-display">
            {progress.current != null
              ? `${progress.current.toLocaleString()} / ${progress.goal.toLocaleString()}`
              : `— / ${progress.goal.toLocaleString()}`}
          </p>
        </div>
      )}
    </div>
  );
}
