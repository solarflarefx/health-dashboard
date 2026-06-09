import { Activity, AlertCircle, Heart, TrendingUp } from 'lucide-react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { SectionPanel } from '@/components/dashboard/SectionPanel';
import { VO2MaxChart } from '@/components/dashboard/VO2MaxChart';
import {
  fetchTodayMetrics,
  fetchHeartHealthMetrics,
  fetchMovementMetrics,
  fetchVO2MaxTrend,
} from '@/lib/api';
import type { HeartHealthMetrics, MovementMetrics, TodayMetrics } from '@/types/dashboard';
import type { VO2MaxTrend } from '@/lib/api';

function DashboardContent({
  today,
  heartHealth,
  movement,
  vo2max,
}: {
  today: TodayMetrics;
  heartHealth: HeartHealthMetrics;
  movement: MovementMetrics;
  vo2max: VO2MaxTrend;
}) {
  const dateLabel = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <main className="min-h-screen p-6 md:p-10">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-text-primary mb-2">
            Health Dashboard
          </h1>
          <p className="text-text-secondary">{dateLabel}</p>
        </div>

        <div className="space-y-4">
          {/* Today */}
          <SectionPanel
            title="Today"
            icon={<Activity className="w-5 h-5 text-accent-blue" />}
            columns={3}
          >
            <MetricCard
              label="Steps"
              value={today.steps != null ? today.steps.toLocaleString() : null}
              color="green"
              progress={
                today.stepsGoal > 0
                  ? { current: today.steps, goal: today.stepsGoal }
                  : undefined
              }
            />
            <MetricCard
              label="Active Calories"
              value={today.activeCalories}
              unit="kcal"
              color="blue"
            />
            <MetricCard
              label="Activity Time"
              value={today.activityTime}
              unit="min"
            />
          </SectionPanel>

          {/* Heart Health */}
          <SectionPanel
            title="Heart Health"
            icon={<Heart className="w-5 h-5 text-accent-coral" />}
            columns={4}
          >
            <MetricCard
              label="Resting HR"
              value={heartHealth.restingHR}
              unit="bpm"
            />
            <MetricCard
              label="Min HR"
              value={heartHealth.minHR}
              unit="bpm"
              color="blue"
            />
            <MetricCard
              label="Max HR"
              value={heartHealth.maxHR}
              unit="bpm"
              color="coral"
            />
            <MetricCard
              label="Stress Score"
              value={heartHealth.stressScore}
              unit="/100"
              progress={{ current: heartHealth.stressScore, goal: 100 }}
              barColor="#60a5fa"
            />
          </SectionPanel>

          {/* Movement */}
          <SectionPanel
            title="Movement"
            icon={<TrendingUp className="w-5 h-5 text-accent-green" />}
            columns={4}
          >
            <MetricCard
              label="Weekly Activities"
              value={movement.weeklyActivities}
              color="green"
            />
            <MetricCard
              label="Intensity Minutes"
              value={movement.intensityMinutes}
              unit="min"
              color="green"
              progress={{ current: movement.intensityMinutes, goal: movement.intensityGoal }}
            />
            <MetricCard
              label="Distance"
              value={movement.distance}
              unit="km"
            />
            <MetricCard
              label="Elevation"
              value={movement.elevation}
              unit="m"
            />
          </SectionPanel>

          {/* VO₂ Max Trend */}
          <SectionPanel title="VO₂ Max Trend" columns={1}>
            <VO2MaxChart trend={vo2max} />
          </SectionPanel>
        </div>
      </div>
    </main>
  );
}

export default async function Home() {
  let today: TodayMetrics;
  let heartHealth: HeartHealthMetrics;
  let movement: MovementMetrics;
  let vo2max: VO2MaxTrend;

  try {
    [today, heartHealth, movement, vo2max] = await Promise.all([
      fetchTodayMetrics(),
      fetchHeartHealthMetrics(),
      fetchMovementMetrics(),
      fetchVO2MaxTrend(),
    ]);
  } catch (err) {
    const message =
      err instanceof Error ? err.message : 'Unable to load health data. Please try again.';
    return (
      <main className="min-h-screen p-6 md:p-10 flex items-center justify-center">
        <div
          className="max-w-md rounded-lg border border-background-hover bg-background-card p-8 text-center"
          role="alert"
        >
          <AlertCircle className="w-10 h-10 text-accent-coral mx-auto mb-4" aria-hidden />
          <h1 className="text-lg font-semibold text-text-primary mb-2">
            Could not load dashboard
          </h1>
          <p className="text-sm text-text-secondary">{message}</p>
        </div>
      </main>
    );
  }

  return (
    <DashboardContent
      today={today}
      heartHealth={heartHealth}
      movement={movement}
      vo2max={vo2max}
    />
  );
}
