import { useState } from 'react';
import { mockAnalysis } from '../data/mockAnalysis';

/*
  Charts for the crop-rotation analysis (POST /api/analyze/).

  Usage:
    <Charts />                         -> shows mock data
    <Charts analysis={apiResponse} />  -> shows real backend data

  No chart library: bars are plain divs sized by width %.
*/

// Each strategy always keeps the same color (color follows the strategy, not its rank)
const STRATEGY_COLORS = {
  current: '#2a78d6', // blue
  water_saver: '#eb6834', // orange
  soil_builder: '#1baf7a', // aqua
};
const FALLBACK_COLOR = '#8a8986';

// Score fields from the API contract (section 6.5), in display order
const METRICS = [
  { key: 'water_fit', label: 'Water fit' },
  { key: 'climate_risk', label: 'Climate resilience' },
  { key: 'soil_health', label: 'Soil health' },
  { key: 'erosion_infiltration', label: 'Erosion & infiltration' },
  { key: 'pest_break', label: 'Pest break' },
  { key: 'income', label: 'Income indicator' },
];

const GRID_STEPS = [0, 25, 50, 75, 100];

const colorOf = (key) => STRATEGY_COLORS[key] ?? FALLBACK_COLOR;

/* ---------- Small pieces ---------- */

function Card({ title, subtitle, action, children }) {
  return (
    <section className="bg-white border border-gray-200 rounded-xl shadow-xs">
      <div className="flex items-start justify-between gap-4 px-6 pt-5">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="px-6 pb-6 pt-4">{children}</div>
    </section>
  );
}

function Legend({ strategies }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-600">
      {strategies.map((s) => (
        <li key={s.key} className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ background: colorOf(s.key) }}
            aria-hidden="true"
          />
          {s.name}
        </li>
      ))}
    </ul>
  );
}

function Delta({ value, baseline }) {
  if (baseline == null) return <span className="text-gray-400">baseline</span>;
  const diff = Math.round((value - baseline) * 10) / 10; // avoid 1.7000000000000028
  if (diff === 0) return <span className="text-gray-500">no change</span>;
  return (
    <span className={diff > 0 ? 'text-emerald-700' : 'text-rose-700'}>
      {diff > 0 ? '▲' : '▼'} {Math.abs(diff)} vs current
    </span>
  );
}

/* ---------- 1. Overall score tiles ---------- */

function OverallScores({ strategies }) {
  const best = Math.max(...strategies.map((s) => s.scores.overall));

  return (
    <div id='charts' className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {strategies.map((s) => {
        const value = s.scores.overall;
        return (
          <div key={s.key} className="p-5 bg-white border border-gray-200 rounded-xl shadow-xs">
            <div className="flex items-center justify-between">
              <p className="flex items-center gap-2 text-sm font-medium text-gray-600">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ background: colorOf(s.key) }}
                  aria-hidden="true"
                />
                {s.name}
              </p>
              {value === best && (
                <span className="px-2 py-0.5 text-xs font-semibold text-emerald-800 bg-emerald-50 rounded-full">
                  ★ Best fit
                </span>
              )}
            </div>

            <p className="mt-3 text-3xl font-bold text-gray-900 tabular-nums">
              {value}
              <span className="text-base font-medium text-gray-400">/100</span>
            </p>

            {/* Thin progress meter */}
            <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${value}%`, background: colorOf(s.key) }}
              />
            </div>

            <p className="mt-2 text-xs font-medium">
              <Delta value={value} baseline={s.baseline_scores?.overall} />
            </p>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- 2. Score breakdown (grouped horizontal bars) ---------- */

function ScoreBreakdown({ strategies }) {
  const [hover, setHover] = useState(null); // { metric, key }

  return (
    <div>
      <Legend strategies={strategies} />

      <div className="mt-5 grid grid-cols-[minmax(110px,160px)_1fr] gap-x-4">
        {/* Axis labels row */}
        <div />
        <div className="relative h-5 text-xs text-gray-400 tabular-nums">
          {GRID_STEPS.map((g) => (
            <span
              key={g}
              className="absolute -translate-x-1/2"
              style={{ left: `${g}%` }}
            >
              {g}
            </span>
          ))}
        </div>

        {METRICS.map((m) => (
          <div key={m.key} className="contents">
            <div className="flex items-center py-3 text-sm text-gray-700 border-t border-gray-100">
              {m.label}
            </div>

            <div className="relative py-3 border-t border-gray-100">
              {/* Recessive gridlines */}
              {GRID_STEPS.map((g) => (
                <span
                  key={g}
                  className="absolute top-0 bottom-0 w-px bg-gray-100"
                  style={{ left: `${g}%` }}
                  aria-hidden="true"
                />
              ))}

              <div className="relative flex flex-col gap-0.5">
                {strategies.map((s) => {
                  const value = s.scores[m.key];
                  const isHover = hover?.metric === m.key && hover?.key === s.key;
                  const dimmed = hover && hover.metric === m.key && !isHover;

                  return (
                    <div
                      key={s.key}
                      className="relative py-0.5 cursor-default" /* taller hit area than the bar */
                      onMouseEnter={() => setHover({ metric: m.key, key: s.key })}
                      onMouseLeave={() => setHover(null)}
                    >
                      <div
                        className="h-2.5 transition-opacity"
                        style={{
                          width: `${value}%`,
                          background: colorOf(s.key),
                          borderRadius: '0 4px 4px 0',
                          opacity: dimmed ? 0.35 : 1,
                        }}
                      />

                      {isHover && (
                        <div
                          role="tooltip"
                          className="absolute z-10 bottom-full mb-1.5 px-3 py-2 text-xs bg-gray-900 text-white rounded-lg shadow-lg whitespace-nowrap pointer-events-none"
                          style={{ left: `min(${value}%, calc(100% - 180px))` }}
                        >
                          <div className="font-semibold">{s.name}</div>
                          <div className="text-gray-300">
                            {m.label}: <span className="font-semibold text-white">{value}</span>/100
                          </div>
                          {s.baseline_scores && (
                            <div className="text-gray-300">
                              Current rotation: {s.baseline_scores[m.key]}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 3. Table view (accessible / exact numbers) ---------- */

function ScoreTable({ strategies }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="text-xs font-semibold text-gray-500 uppercase border-b border-gray-200">
            <th className="py-2 pr-4">Score</th>
            {strategies.map((s) => (
              <th key={s.key} className="py-2 px-3 text-right">{s.name}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 tabular-nums">
          {[{ key: 'overall', label: 'Overall' }, ...METRICS].map((m) => (
            <tr key={m.key}>
              <td className="py-2 pr-4 text-gray-700">{m.label}</td>
              {strategies.map((s) => (
                <td key={s.key} className="py-2 px-3 text-right text-gray-900">
                  {s.scores[m.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Main component ---------- */

export default function Charts({ analysis = mockAnalysis }) {
  const [showTable, setShowTable] = useState(false);
  const strategies = analysis?.strategies ?? [];

  if (strategies.length === 0) {
    return (
      <Card title="Rotation analysis">
        <p className="text-sm text-gray-500">No analysis yet. Submit your farm details to see results.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <OverallScores strategies={strategies} />

      <Card
        title="Score breakdown"
        subtitle="How each rotation strategy scores (0–100, higher is better)"
        action={
          <button
            type="button"
            onClick={() => setShowTable((v) => !v)}
            className="shrink-0 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
          >
            {showTable ? 'Show chart' : 'Show table'}
          </button>
        }
      >
        {showTable ? (
          <ScoreTable strategies={strategies} />
        ) : (
          <ScoreBreakdown strategies={strategies} />
        )}
      </Card>
    </div>
  );
}
