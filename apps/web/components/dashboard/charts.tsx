'use client';

import { useId } from 'react';

// Lightweight, dependency-free SVG charts tuned for the VoixAI dark theme.
// Everything scales via viewBox so the charts stay crisp at any width.

interface AreaPoint {
  label: string;
  value: number;
}

export function AreaChart({
  data,
  height = 220,
  color = 'var(--voix-accent)',
  valueSuffix = '',
}: {
  data: AreaPoint[];
  height?: number;
  color?: string;
  valueSuffix?: string;
}) {
  const gradientId = useId();
  const width = 720;
  const padX = 8;
  const padY = 16;
  const max = Math.max(1, ...data.map((d) => d.value));
  const stepX = data.length > 1 ? (width - padX * 2) / (data.length - 1) : 0;

  const points = data.map((d, i) => {
    const x = padX + i * stepX;
    const y = padY + (1 - d.value / max) * (height - padY * 2);
    return { x, y, ...d };
  });

  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ');
  const areaPath =
    points.length > 0
      ? `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${height - padY} L ${points[0].x.toFixed(1)} ${height - padY} Z`
      : '';

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-full w-full"
      preserveAspectRatio="none"
      role="img"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line
          key={g}
          x1={padX}
          x2={width - padX}
          y1={padY + g * (height - padY * 2)}
          y2={padY + g * (height - padY * 2)}
          stroke="var(--voix-border-subtle)"
          strokeWidth="1"
        />
      ))}
      {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} />}
      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill={color}>
          <title>{`${p.label}: ${p.value}${valueSuffix}`}</title>
        </circle>
      ))}
    </svg>
  );
}

export function BarPairChart({
  data,
  height = 220,
}: {
  data: { label: string; a: number; b: number }[];
  height?: number;
}) {
  const aId = useId();
  const bId = useId();
  const width = 720;
  const padX = 8;
  const padY = 16;
  const max = Math.max(1, ...data.map((d) => d.a));
  const groupW = (width - padX * 2) / Math.max(1, data.length);
  const barW = Math.min(18, groupW * 0.34);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-full w-full"
      preserveAspectRatio="none"
      role="img"
    >
      <defs>
        <linearGradient id={aId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--voix-accent)" stopOpacity="0.95" />
          <stop offset="100%" stopColor="var(--voix-accent)" stopOpacity="0.55" />
        </linearGradient>
        <linearGradient id={bId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--voix-success)" stopOpacity="0.95" />
          <stop offset="100%" stopColor="var(--voix-success)" stopOpacity="0.55" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line
          key={g}
          x1={padX}
          x2={width - padX}
          y1={padY + g * (height - padY * 2)}
          y2={padY + g * (height - padY * 2)}
          stroke="var(--voix-border-subtle)"
          strokeWidth="1"
        />
      ))}
      {data.map((d, i) => {
        const cx = padX + i * groupW + groupW / 2;
        const aH = (d.a / max) * (height - padY * 2);
        const bH = (d.b / max) * (height - padY * 2);
        return (
          <g key={i}>
            <rect
              x={cx - barW - 2}
              y={height - padY - aH}
              width={barW}
              height={Math.max(0, aH)}
              rx="4"
              fill={`url(#${aId})`}
            >
              <title>{`${d.label} · calls: ${d.a}`}</title>
            </rect>
            <rect
              x={cx + 2}
              y={height - padY - bH}
              width={barW}
              height={Math.max(0, bH)}
              rx="4"
              fill={`url(#${bId})`}
            >
              <title>{`${d.label} · orders: ${d.b}`}</title>
            </rect>
          </g>
        );
      })}
    </svg>
  );
}

export interface DonutSlice {
  label: string;
  value: number;
  color: string;
}

export function DonutChart({ slices, size = 180 }: { slices: DonutSlice[]; size?: number }) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const radius = size / 2;
  const stroke = 22;
  const r = radius - stroke / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className="flex items-center gap-5">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        className="shrink-0 -rotate-90"
      >
        <circle
          cx={radius}
          cy={radius}
          r={r}
          fill="none"
          stroke="var(--voix-border-subtle)"
          strokeWidth={stroke}
        />
        {total > 0 &&
          slices.map((s, i) => {
            const frac = s.value / total;
            const dash = frac * circ;
            const seg = (
              <circle
                key={i}
                cx={radius}
                cy={radius}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth={stroke}
                strokeDasharray={`${dash} ${circ - dash}`}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
              >
                <title>{`${s.label}: ${s.value}`}</title>
              </circle>
            );
            offset += dash;
            return seg;
          })}
      </svg>
      <div className="flex flex-col gap-2">
        {slices.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-[var(--voix-text-secondary)]">{s.label}</span>
            <span className="ml-auto font-semibold text-[var(--voix-text-primary)]">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Sparkline({
  values,
  color = 'var(--voix-accent)',
}: {
  values: number[];
  color?: string;
}) {
  const width = 120;
  const height = 36;
  const max = Math.max(1, ...values);
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  const path = values
    .map(
      (v, i) =>
        `${i === 0 ? 'M' : 'L'} ${(i * stepX).toFixed(1)} ${(height - (v / max) * height).toFixed(1)}`
    )
    .join(' ');
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-9 w-full" preserveAspectRatio="none">
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
