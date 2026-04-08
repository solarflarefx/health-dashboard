import { render, screen } from '@testing-library/react';
import { MetricCard } from '../MetricCard';

describe('MetricCard', () => {
  it('renders label, value, and unit correctly', () => {
    render(<MetricCard label="Heart Rate" value={72} unit="bpm" />);

    expect(screen.getByText('Heart Rate')).toBeInTheDocument();
    expect(screen.getByText('72')).toBeInTheDocument();
    expect(screen.getByText('bpm')).toBeInTheDocument();
  });

  it('applies green accent color class when color="green"', () => {
    render(<MetricCard label="Steps" value={8000} color="green" />);

    expect(screen.getByText('8000')).toHaveClass('text-accent-green');
  });

  it('applies coral accent color class when color="coral"', () => {
    render(<MetricCard label="Stress" value={42} color="coral" />);

    expect(screen.getByText('42')).toHaveClass('text-accent-coral');
  });

  it('applies blue accent color class when color="blue"', () => {
    render(<MetricCard label="VO2 Max" value={52} color="blue" />);

    expect(screen.getByText('52')).toHaveClass('text-accent-blue');
  });

  it('shows progress bar when progress is provided', () => {
    render(
      <MetricCard
        label="Steps"
        value={8000}
        progress={{ current: 8000, goal: 10000 }}
      />,
    );

    // The progress bar fill div has an inline width style
    const progressBar = document.querySelector('[style*="width"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('hides progress bar when progress is not provided', () => {
    render(<MetricCard label="Heart Rate" value={72} />);

    const progressBar = document.querySelector('[style*="width"]');
    expect(progressBar).not.toBeInTheDocument();
  });

  it('progress bar width reflects progressValue correctly', () => {
    render(
      <MetricCard
        label="Steps"
        value={7500}
        progress={{ current: 7500, goal: 10000 }}
      />,
    );

    // 7500 / 10000 = 75%
    const progressBar = document.querySelector('[style*="width"]') as HTMLElement;
    expect(progressBar).toHaveStyle({ width: '75%' });
  });

  it('clamps progress bar width to 100% when current exceeds goal', () => {
    render(
      <MetricCard
        label="Steps"
        value={12000}
        progress={{ current: 12000, goal: 10000 }}
      />,
    );

    const progressBar = document.querySelector('[style*="width"]') as HTMLElement;
    expect(progressBar).toHaveStyle({ width: '100%' });
  });
});
