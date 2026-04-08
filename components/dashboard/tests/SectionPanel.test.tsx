import { render, screen } from '@testing-library/react';
import { SectionPanel } from '../SectionPanel';

describe('SectionPanel', () => {
  it('renders title correctly', () => {
    render(<SectionPanel title="Heart Health">{<div />}</SectionPanel>);

    expect(screen.getByRole('heading', { name: 'Heart Health' })).toBeInTheDocument();
  });

  it('renders children correctly', () => {
    render(
      <SectionPanel title="Today">
        <span>Metric One</span>
        <span>Metric Two</span>
      </SectionPanel>,
    );

    expect(screen.getByText('Metric One')).toBeInTheDocument();
    expect(screen.getByText('Metric Two')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(
      <SectionPanel title="Movement" icon={<svg data-testid="section-icon" aria-hidden="true" />}>
        <div />
      </SectionPanel>,
    );

    expect(screen.getByTestId('section-icon')).toBeInTheDocument();
  });

  it('does not render icon slot when icon is not provided', () => {
    render(
      <SectionPanel title="Movement">
        <div />
      </SectionPanel>,
    );

    expect(screen.queryByTestId('section-icon')).not.toBeInTheDocument();
  });
});
