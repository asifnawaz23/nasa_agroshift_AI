import { useState } from 'react';

/*
  Step 5 + 6: compare the three rotations side by side.
  Reads `strategy.comparison` from POST /api/analyze/ (backend engine/compare.py):
  crop sequence, climate suitability, water need, soil improvement, nitrogen fixing,
  pest/disease risk, benefits, limitations, evidence and data sources.
  Levels always show an icon + word, never color alone.
*/

const STRATEGY_STYLE = {
  current: { label: 'Existing rotation', accent: 'border-t-[#2a78d6]', dot: '#2a78d6' },
  water_saver: { label: 'Water-saving rotation', accent: 'border-t-[#eb6834]', dot: '#eb6834' },
  soil_builder: { label: 'Soil-improvement rotation', accent: 'border-t-[#1baf7a]', dot: '#1baf7a' },
};

const LEVEL = {
  good: ['✅', 'Good', 'bg-emerald-50 text-emerald-800 border-emerald-200'],
  fair: ['⚠️', 'Fair', 'bg-amber-50 text-amber-800 border-amber-200'],
  poor: ['❗', 'Poor', 'bg-red-50 text-red-700 border-red-200'],
  strong: ['✅', 'Strong', 'bg-emerald-50 text-emerald-800 border-emerald-200'],
  some: ['➕', 'Some', 'bg-sky-50 text-sky-800 border-sky-200'],
  none: ['➖', 'None', 'bg-slate-100 text-slate-600 border-slate-200'],
  low: ['✅', 'Low risk', 'bg-emerald-50 text-emerald-800 border-emerald-200'],
  moderate: ['⚠️', 'Moderate risk', 'bg-amber-50 text-amber-800 border-amber-200'],
  high: ['❗', 'High risk', 'bg-red-50 text-red-700 border-red-200'],
  unknown: ['•', 'No data', 'bg-slate-100 text-slate-600 border-slate-200'],
};

function Badge({ level }) {
  const [icon, word, tone] = LEVEL[level] ?? LEVEL.unknown;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold rounded-full border ${tone}`}>
      <span aria-hidden="true">{icon}</span>{word}
    </span>
  );
}

function Row({ icon, title, level, score, children }) {
  return (
    <div className="py-3 border-t border-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          <span aria-hidden="true">{icon}</span> {title}
        </p>
        <div className="flex items-center gap-2">
          {score != null && <span className="text-xs tabular-nums text-slate-500">{Math.round(score)}/100</span>}
          {level && <Badge level={level} />}
        </div>
      </div>
      <div className="mt-1.5 text-sm text-slate-700 space-y-1">{children}</div>
    </div>
  );
}

const list = (items) => (items?.length ? items.join(', ') : '—');

function StrategyColumn({ strategy, best }) {
  const [open, setOpen] = useState(false);
  const c = strategy.comparison;
  const style = STRATEGY_STYLE[strategy.key] ?? { label: strategy.name, accent: 'border-t-slate-400', dot: '#8a8986' };
  const water = c.water;

  return (
    <article className={`flex flex-col p-5 rounded-2xl bg-white border border-slate-200 border-t-4 ${style.accent} shadow-sm`}>
      <header>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{style.label}</p>
            <h3 className="mt-0.5 text-base font-bold text-slate-900">{strategy.name}</h3>
          </div>
          <div className="text-right">
            <p className="text-2xl font-extrabold text-slate-900 tabular-nums">{Math.round(strategy.scores.overall)}</p>
            <p className="text-[11px] text-slate-500">overall /100</p>
          </div>
        </div>
        {best && (
          <span className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-bold rounded-full bg-amber-100 text-amber-900 border border-amber-200">
            ★ Best fit for your priorities
          </span>
        )}
      </header>

      {/* Crop sequence */}
      <div className="mt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">🔁 Crop sequence</p>
        <ol className="mt-2 flex flex-wrap items-center gap-1.5">
          {c.sequence.map((s, i) => (
            <li key={`${s.crop}-${i}`} className="flex items-center gap-1.5">
              <span
                className={`px-2 py-1 text-xs rounded-lg border ${s.n_fixing ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-slate-50 border-slate-200 text-slate-800'}`}
                title={`${s.season}, ${s.months}`}
              >
                <span className="font-semibold">{s.name.split(' (')[0]}</span>
                {s.name_ur && <span className="ms-1 text-slate-500" lang="ur">{s.name_ur}</span>}
                <span className="block text-[10px] text-slate-500">{s.season.split(' ')[0]} · {s.months}</span>
              </span>
              {i < c.sequence.length - 1 && <span className="text-slate-400" aria-hidden="true">→</span>}
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-2">
        <Row icon="🌡️" title="Climate suitability" level={c.climate.level} score={c.climate.score}>
          <p>Heat-tolerant: {list(c.climate.heat_tolerant)}</p>
          {c.climate.heat_sensitive.length > 0 && <p>Heat-sensitive: {list(c.climate.heat_sensitive)}</p>}
          {c.climate.drought_tolerant.length > 0 && <p>Drought-tolerant: {list(c.climate.drought_tolerant)}</p>}
        </Row>

        <Row icon="💧" title="Water requirement" level={water.level} score={water.score}>
          <p>
            Needs about <strong className="tabular-nums">{water.need_mm_per_year ?? '—'} mm</strong> a year
            {water.rain_mm_per_year != null && <> vs <span className="tabular-nums">{water.rain_mm_per_year} mm</span> rain</>}.
          </p>
          {water.irrigation_gap_mm > 0 && (
            <p>Irrigation gap: <strong className="tabular-nums">~{water.irrigation_gap_mm} mm</strong></p>
          )}
          {water.vs_current_pct != null && water.vs_current_pct !== 0 && (
            <p className={water.vs_current_pct < 0 ? 'text-emerald-800' : 'text-red-700'}>
              {water.vs_current_pct < 0 ? '▼' : '▲'} {Math.abs(water.vs_current_pct)}% {water.vs_current_pct < 0 ? 'less' : 'more'} water than your current rotation
            </p>
          )}
        </Row>

        <Row icon="🌱" title="Soil improvement" level={c.soil.level} score={c.soil.score}>
          <p>Deep roots: {list(c.soil.deep_rooted)}</p>
          <p>Adds organic matter: {list(c.soil.high_residue)}</p>
        </Row>

        <Row icon="🫘" title="Nitrogen fixing" level={c.nitrogen.level}>
          {c.nitrogen.n_fixing_crops.length > 0 ? (
            <p>{list(c.nitrogen.n_fixing_crops)} take nitrogen from the air, so the next crop needs less fertilizer.</p>
          ) : (
            <p>No nitrogen-fixing crop in this rotation.</p>
          )}
        </Row>

        <Row icon="🐛" title="Pest & disease risk" level={c.pest.risk} score={c.pest.score}>
          <p>{c.pest.families.length} crop famil{c.pest.families.length === 1 ? 'y' : 'ies'}: {list(c.pest.families)}</p>
          {c.pest.same_family_in_a_row.length > 0 && <p>Same family in a row: {list(c.pest.same_family_in_a_row)}</p>}
          <p className="text-xs text-slate-500">{c.pest.notes[0]}</p>
        </Row>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mt-3 self-start px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
      >
        {open ? 'Hide' : 'Show'} benefits, limitations & evidence
      </button>

      {open && (
        <div className="mt-3 space-y-3 text-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">👍 Benefits</p>
            <ul className="mt-1 list-disc ps-5 space-y-1 text-slate-700">
              {c.benefits.length ? c.benefits.map((b, i) => <li key={i}>{b}</li>) : <li>—</li>}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">⚠️ Limitations</p>
            <ul className="mt-1 list-disc ps-5 space-y-1 text-slate-700">
              {c.limitations.length ? c.limitations.map((b, i) => <li key={i}>{b}</li>) : <li>—</li>}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-800">📊 Evidence</p>
            <ul className="mt-1 list-disc ps-5 space-y-1 text-slate-700">
              {c.evidence.length ? c.evidence.map((e, i) => (
                <li key={i}>{e.text} <span className="text-xs text-slate-400">({e.source})</span></li>
              )) : <li>—</li>}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">📚 Data sources</p>
            <p className="mt-1 text-xs text-slate-600">{list(c.data_sources)}</p>
            <ul className="mt-1 space-y-0.5 text-xs text-slate-500">
              {c.crop_sources.map((s) => <li key={s}>{s}</li>)}
            </ul>
          </div>
        </div>
      )}
    </article>
  );
}

export default function StrategyComparison({ analysis }) {
  const strategies = (analysis?.strategies ?? []).filter((s) => s.comparison);
  if (strategies.length === 0) return null;
  const best = strategies.reduce((a, b) => (b.scores.overall > a.scores.overall ? b : a));
  const simulated = strategies.some((s) => s.baseline_scores);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">🔍 Compare the 3 rotation strategies</p>
          <p className="text-xs text-slate-500">
            Existing, water-saving and soil-improvement rotations for your farm and priorities.
            {simulated ? ' Scores are SIMULATED for the What-If climate.' : ' Based on 2006–2025 NASA data.'}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {strategies.map((s) => (
          <StrategyColumn key={s.key} strategy={s} best={s.key === best.key} />
        ))}
      </div>
      <p className="text-xs text-slate-500">
        Water needs and crop traits come from the crop table (FAO sources per crop). Sowing months are typical
        regional values. Check any change with your local agriculture extension office.
      </p>
    </div>
  );
}
