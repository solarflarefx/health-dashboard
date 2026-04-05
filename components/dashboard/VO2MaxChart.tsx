'use client';

import { useRef, useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  type ChartData,
  type ChartOptions,
  type Plugin,
  type TooltipModel,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { TrendingUp } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const LABELS = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10', 'W11', 'W12'];
const DATA_POINTS = [42, 43, 42, 44, 45, 44, 46, 47, 46, 48, 48, 49];

/** Draws a dashed vertical rule at the active x position, matching Figma Make crosshair behavior. */
const crosshairPlugin: Plugin<'line'> = {
  id: 'crosshair',
  afterDraw(chart) {
    const active = chart.tooltip?.getActiveElements();
    if (!active?.length) return;

    const x = active[0].element.x;
    const { top, bottom } = chart.scales.y;
    const { ctx } = chart;

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#30363d';
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.restore();
  },
};

// ─── External HTML tooltip (needed for the VO₂ subscript) ───────────────────

function getOrCreateTooltipEl(chart: ChartJS): HTMLDivElement {
  const container = chart.canvas.parentNode as HTMLElement;
  let el = container.querySelector<HTMLDivElement>('[data-vo2-tooltip]');
  if (!el) {
    el = document.createElement('div');
    el.setAttribute('data-vo2-tooltip', '');
    Object.assign(el.style, {
      position: 'absolute',
      pointerEvents: 'none',
      opacity: '0',
      transition: 'opacity 0.15s ease',
      zIndex: '10',
    });
    container.appendChild(el);
  }
  return el;
}

function externalTooltipHandler(context: {
  chart: ChartJS;
  tooltip: TooltipModel<'line'>;
}) {
  const { chart, tooltip } = context;
  const el = getOrCreateTooltipEl(chart);

  if (tooltip.opacity === 0) {
    el.style.opacity = '0';
    return;
  }

  const week = tooltip.title?.[0] ?? '';
  const value = tooltip.dataPoints?.[0]?.parsed.y ?? '';

  el.innerHTML = `
    <div style="
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 6px;
      padding: 10px;
      min-width: 120px;
      white-space: nowrap;
      line-height: 1.6;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    ">
      <div style="color:#7d8590; font-size:13px; margin-bottom:3px;">${week}</div>
      <div style="color:#ffffff; font-size:16px; font-weight:700;">
        VO<sub style="font-size:10px; vertical-align:sub;">2</sub> Max:&nbsp;<span style="color:#60a5fa;">${value}</span>
      </div>
    </div>
  `;

  // Position relative to the canvas parent (the `.relative` wrapper)
  const canvasRect = chart.canvas.getBoundingClientRect();
  const containerRect = (chart.canvas.parentNode as HTMLElement).getBoundingClientRect();
  const offsetX = canvasRect.left - containerRect.left;
  const offsetY = canvasRect.top - containerRect.top;

  el.style.opacity = '1';
  el.style.left = `${offsetX + tooltip.caretX + 14}px`;
  el.style.top = `${offsetY + tooltip.caretY - 48}px`;
}

// ─── Chart config ────────────────────────────────────────────────────────────

const CHART_OPTIONS: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 3,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: false,
      external: externalTooltipHandler,
    },
  },
  scales: {
    x: {
      grid: { color: '#21262d' },
      ticks: { color: '#7d8590', font: { size: 12 } },
      border: { display: false },
    },
    y: {
      min: 40,
      max: 52,
      grid: { color: '#21262d' },
      ticks: { color: '#7d8590', font: { size: 12 }, stepSize: 2 },
      border: { display: false },
    },
  },
};

const BASE_DATASET: ChartData<'line'>['datasets'][0] = {
  data: DATA_POINTS,
  borderColor: '#60a5fa',
  backgroundColor: 'rgba(96, 165, 250, 0.15)',
  fill: true,
  tension: 0.4,
  pointRadius: 5,
  pointBackgroundColor: '#60a5fa',
  pointBorderColor: '#0d1117',
  pointBorderWidth: 2,
  pointHoverRadius: 8,
  pointHoverBackgroundColor: '#60a5fa',
  pointHoverBorderColor: '#0d1117',
  pointHoverBorderWidth: 2,
};

// ─── Component ───────────────────────────────────────────────────────────────

/** Line chart showing VO₂ Max progression over 12 weeks with gradient fill, crosshair, and HTML tooltip. */
export function VO2MaxChart() {
  const chartRef = useRef<ChartJS<'line'>>(null);
  const [chartData, setChartData] = useState<ChartData<'line'>>({
    labels: LABELS,
    datasets: [BASE_DATASET],
  });

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const gradient = chart.ctx.createLinearGradient(0, 0, 0, chart.height);
    gradient.addColorStop(0, 'rgba(96, 165, 250, 0.25)');
    gradient.addColorStop(1, 'rgba(96, 165, 250, 0)');

    setChartData({
      labels: LABELS,
      datasets: [{ ...BASE_DATASET, backgroundColor: gradient }],
    });
  }, []);

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-6">
        <span
          className="text-3xl text-text-primary"
          style={{
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            letterSpacing: '0',
            fontVariantNumeric: 'tabular-nums',
            whiteSpace: 'nowrap',
          }}
        >49.0</span>
        <span className="text-sm text-text-secondary">ml/kg/min</span>
        <div className="flex items-center gap-1 ml-2">
          <TrendingUp className="w-4 h-4 text-accent-green" />
          <span className="text-sm font-mono-display text-accent-green">+0.8 this month</span>
        </div>
      </div>

      {/* position:relative gives the absolute-positioned tooltip an anchor */}
      <div className="relative">
        <Line
          ref={chartRef}
          data={chartData}
          options={CHART_OPTIONS}
          plugins={[crosshairPlugin]}
        />
      </div>
    </div>
  );
}
