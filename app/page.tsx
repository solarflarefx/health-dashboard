import { Activity, Heart, TrendingUp } from 'lucide-react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { SectionPanel } from '@/components/dashboard/SectionPanel';
import { VO2MaxChart } from '@/components/dashboard/VO2MaxChart';
import type {
  TodayMetrics,
  HeartHealthMetrics,
  MovementMetrics,
} from '@/types/dashboard';

const today: TodayMetrics = {
  steps: 8742,
  stepsGoal: 10000,
  activeCalories: 487,
  activityTime: 52,
};

const heartHealth: HeartHealthMetrics = {
  restingHR: 58,
  minHR: 54,
  maxHR: 162,
  stressScore: 32,
};

const movement: MovementMetrics = {
  weeklyActivities: 6,
  intensityMinutes: 234,
  intensityGoal: 150,
  distance: 42.7,
  elevation: 387,
};

export default function Home() {
  return (
    <main className="min-h-screen p-6 md:p-10">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-text-primary mb-2">
            Health Dashboard
          </h1>
          <p className="text-text-secondary">Saturday, April 4, 2026</p>
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
              value={today.steps.toLocaleString()}
              color="green"
              progress={{ current: today.steps, goal: today.stepsGoal }}
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
            <VO2MaxChart />
          </SectionPanel>
        </div>
      </div>
    </main>
  );
}
