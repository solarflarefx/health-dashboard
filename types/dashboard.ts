import type { ReactNode } from 'react';

/** Semantic accent colors mapped to the Midnight Terminal palette */
export type AccentColor = 'green' | 'blue' | 'coral' | 'default';

export interface ProgressData {
  current: number;
  goal: number;
}

export interface MetricCardProps {
  /** Short human-readable label shown above the value */
  label: string;
  /** Numeric or pre-formatted string value */
  value: number | string;
  /** Unit suffix shown next to the value (e.g. "kcal", "min") */
  unit?: string;
  /** Accent color token for the value and progress bar */
  color?: AccentColor;
  /** When provided renders a progress bar below the value */
  progress?: ProgressData;
  /** Explicit hex color for the progress bar fill, overrides the accent token */
  barColor?: string;
}

export interface SectionPanelProps {
  title: string;
  /** Optional leading icon rendered before the title */
  icon?: ReactNode;
  children: ReactNode;
  /** Number of responsive grid columns for the metric grid */
  columns?: 1 | 2 | 3 | 4;
}

export interface TodayMetrics {
  steps: number;
  stepsGoal: number;
  activeCalories: number;
  activityTime: number;
}

export interface HeartHealthMetrics {
  restingHR: number;
  minHR: number;
  maxHR: number;
  stressScore: number;
}

export interface MovementMetrics {
  weeklyActivities: number;
  intensityMinutes: number;
  intensityGoal: number;
  distance: number;
  elevation: number;
}
