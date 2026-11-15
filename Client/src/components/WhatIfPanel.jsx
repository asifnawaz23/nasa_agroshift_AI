import { useEffect, useRef, useState } from 'react';

/*
  What-If simulator (plan section 7, MUST).
  Two sliders change the climate: temperature (-2 … +5 °C) and rainfall (-50 … +30 %).
  Each change re-runs POST /api/analyze/ with `scenario` (debounced), and the dashboard shows
  the simulated scores and alerts. The backend reuses its cached NASA data, so this is fast.
*/

const SEVERITY_ORDER = ['critical', 'high', 'moderate'];

function countBySeverity(alerts = []) {
  const counts = { critical: 0, high: 0, moderate: 0 };
  alerts.forEach((a) => {
    const level = (a.severity || '').toLowerCase();
    if (level in counts) counts[level] += 1;
  });
  return counts;
}

function Slider({ id, label, value, min, max, step, unit, onChange }) {
  const sign = value > 0 ? '+' : '';
  return (
    <div>
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm font-semibold text-slate-800">{label}</label>
        <span className={`text-sm font-bold tabular-nums ${value === 0 ? 'text-slate-500' : 'text-violet-700'}`}>
          {sign}{value}{unit}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-violet-600 h-2 cursor-pointer"
      />
      <div className="mt-1 flex justify-between text-[11px] text-slate-400 tabular-nums">
        <span>{min}{unit}</span>
        <span>0</span>
        <span>+{max}{unit}</span>
      </div>
    </div>
  );
}

export default function WhatIfPanel({ basePayload, baselineAnalysis, scenarioAnalysis, onRun, onReset }) {
  const [tempC, setTempC] = useState(0);
  const [rainPct, setRainPct] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);
  const firstRender = useRef(true);

  // The dashboard gives this panel a new `key` for each new farm analysis, so the sliders
  // start again from today's climate without an extra effect.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return undefined;
    }
    if (!basePayload) return undefined;
    if (tempC === 0 && rainPct === 0) {
      onReset();
      return undefined;
    }
    const id = ++requestId.current;
    const timer = setTimeout(async () => {
      setRunning(true);
      setError('');
      try {
        await onRun({ temp_c: tempC, rain_pct: rainPct }, () => id === requestId.current);
      } catch (err) {
        if (id === requestId.current) setError(err.message);
      } finally {
        if (id === requestId.current) setRunning(false);
      }
    }, 600);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tempC, rainPct]);

  const active = tempC !== 0 || rainPct !== 0;
  const bigScenario = Math.abs(tempC) > 3 || Math.abs(rainPct) > 30;
  const before = countBySeverity(baselineAnalysis?.alerts);
  const after = countBySeverity(scenarioAnalysis?.alerts);
  const showResult = active && scenarioAnalysis && !running;

  const reset = () => {
    requestId.current += 1; // ignore any request still running
    setTempC(0);
    setRainPct(0);
    setRunning(false);
    setError('');
  };

  if (!basePayload) {
    return (
      <div className="p-5 rounded-2xl bg-white border border-slate-200 text-sm text-slate-500">
        Run an analysis first, then try a hotter or drier future here.
      </div>
    );
  }

  return (
    <div className="p-5 sm:p-6 rounded-2xl bg-white border border-violet-200 shadow-sm space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-600">
            Move the sliders to test a hotter or drier climate. Scores and alerts update below.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {active && (
            <span className="px-2.5 py-1 text-[11px] font-bold tracking-wide rounded-full bg-violet-100 text-violet-800 border border-violet-200">
              SIMULATED
            </span>
          )}
          <button
            type="button"
            onClick={reset}
            disabled={!active}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Reset to today
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Slider id="whatif-temp" label="🌡️ Temperature change" value={tempC} min={-2} max={5} step={0.5} unit=" °C" onChange={setTempC} />
        <Slider id="whatif-rain" label="🌧️ Rainfall change" value={rainPct} min={-50} max={30} step={5} unit="%" onChange={setRainPct} />
      </div>

      {running && (
        <div className="flex items-center gap-2 text-sm text-violet-800">
          <span className="w-4 h-4 rounded-full border-2 border-violet-600 border-t-transparent animate-spin" />
          Re-running the analysis with the simulated climate…
        </div>
      )}
      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}

      {showResult && (
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Overall score: today → simulated</p>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
              {(scenarioAnalysis.strategies ?? []).map((s) => {
                const base = (baselineAnalysis?.strategies ?? []).find((b) => b.key === s.key)?.scores?.overall
                  ?? s.baseline_scores?.overall;
                const now = s.scores?.overall;
                const delta = base != null && now != null ? Math.round((now - base) * 10) / 10 : null;
                return (
                  <div key={s.key} className="p-3 rounded-xl border border-slate-200 bg-slate-50">
                    <p className="text-xs font-semibold text-slate-600">{s.name}</p>
                    <p className="mt-1 text-sm tabular-nums text-slate-900">
                      {base ?? '—'} → <span className="font-bold">{now ?? '—'}</span>
                      {delta != null && delta !== 0 && (
                        <span className={`ml-2 text-xs font-bold ${delta < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                          {delta > 0 ? `▲ +${delta}` : `▼ ${Math.abs(delta)}`}
                        </span>
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Alerts for the current rotation</p>
            <div className="mt-2 flex flex-wrap gap-2 text-sm">
              {SEVERITY_ORDER.map((level) => (
                <span key={level} className="px-3 py-1 rounded-full border border-slate-200 bg-white tabular-nums">
                  <span className="capitalize font-semibold">{level}</span>: {before[level]} → <span className="font-bold">{after[level]}</span>
                </span>
              ))}
            </div>
          </div>

          <p className="text-xs text-slate-500">
            Simulated: we add the temperature change to every day of the 2006–2025 NASA POWER record and scale the
            rainfall, then recompute everything. This is a what-if test, not a forecast.
            {bigScenario && ' Large changes like this give a low-confidence result.'}
          </p>
        </div>
      )}
    </div>
  );
}
