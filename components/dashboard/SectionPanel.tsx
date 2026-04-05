import type { SectionPanelProps } from '@/types/dashboard';

const gridColsMap: Record<NonNullable<SectionPanelProps['columns']>, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-4',
};

/**
 * A full-width section card containing a titled header row and a responsive
 * metric grid. Styled with the Midnight Terminal card background and border tokens.
 */
export function SectionPanel({
  title,
  icon,
  children,
  columns = 3,
}: SectionPanelProps) {
  return (
    <div className="rounded-lg p-6 border bg-background-card border-border-default">
      <div className="flex items-center gap-2 mb-8">
        {icon}
        <h2 className="text-lg font-medium text-text-primary">{title}</h2>
      </div>

      <div className={`grid gap-8 pt-6 ${gridColsMap[columns]}`}>
        {children}
      </div>
    </div>
  );
}
