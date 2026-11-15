import { useEffect, useMemo, useState } from 'react';

/*
  Weather for the farm picked on the map: current conditions + a week of daily data.
  Source: Open-Meteo forecast API (free, no key). This is live weather, NOT the NASA
  history used by the analysis, and the panel says so.

  Charts follow the dataviz rules: one measure per chart (temperature and rain are separate,
  never a dual axis), thin marks, a legend for the two temperature series, hover tooltips,
  and a table view.
*/

const API = 'https://api.open-meteo.com/v1/forecast';
const COLORS = { max: '#eb6834', min: '#2a78d6', rain: '#2a78d6', grid: '#e5e7eb', axis: '#6b7280' };

// WMO weather codes -> short text + emoji (Open-Meteo docs)
const WMO = {
  0: ['Clear sky', '☀️'], 1: ['Mainly clear', '🌤️'], 2: ['Partly cloudy', '⛅'], 3: ['Overcast', '☁️'],
  45: ['Fog', '🌫️'], 48: ['Freezing fog', '🌫️'],
  51: ['Light drizzle', '🌦️'], 53: ['Drizzle', '🌦️'], 55: ['Heavy drizzle', '🌧️'],
  56: ['Freezing drizzle', '🌧️'], 57: ['Freezing drizzle', '🌧️'],
  61: ['Light rain', '🌦️'], 63: ['Rain', '🌧️'], 65: ['Heavy rain', '🌧️'],
  66: ['Freezing rain', '🌧️'], 67: ['Freezing rain', '🌧️'],
  71: ['Light snow', '🌨️'], 73: ['Snow', '🌨️'], 75: ['Heavy snow', '❄️'], 77: ['Snow grains', '🌨️'],
  80: ['Light showers', '🌦️'], 81: ['Showers', '🌧️'], 82: ['Heavy showers', '⛈️'],
  85: ['Snow showers', '🌨️'], 86: ['Snow showers', '🌨️'],
  95: ['Thunderstorm', '⛈️'], 96: ['Thunderstorm, hail', '⛈️'], 99: ['Thunderstorm, hail', '⛈️'],
};
const describe = (code, isDay = 1) => {
  const [text, icon] = WMO[code] ?? ['Unknown', '🌡️'];
  return [text, code <= 1 && !isDay ? '🌙' : icon];
};

const round = (v, d = 0) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d));
const weekday = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'short' });
const dayMonth = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

/* ---------- Charts (plain SVG) ---------- */

const W = 520;
const H = 230;
const PAD = { top: 18, right: 44, bottom: 30, left: 42 };
const innerW = W - PAD.left - PAD.right;
const innerH = H - PAD.top - PAD.bottom;

function niceTicks(min, max, count = 4) {
  const span = max - min || 1;
  const step = [1, 2, 5, 10, 20].map((s) => s * 10 ** Math.floor(Math.log10(span / count)))
    .find((s) => span / s <= count) ?? span / count;
  const start = Math.floor(min / step) * step;
  const ticks = [];
  for (let v = start; v <= max + step * 0.5; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

function Tooltip({ day, x, children }) {
  // Keep the box inside the chart: flip to the left of the pointer on the right half
  const left = `${(x / W) * 100}%`;
  return (
    <div
      className="pointer-events-none absolute top-1 z-10 min-w-[9rem] px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg shadow-md"
      style={{ left, transform: x > W / 2 ? 'translateX(calc(-100% - 10px))' : 'translateX(10px)' }}
      role="status"
    >
      <p className="font-semibold text-slate-900">{weekday(day.date)} {dayMonth(day.date)}</p>
      {children}
    </div>
  );
}

function TemperatureChart({ days }) {
  const [hover, setHover] = useState(null);
  const values = days.flatMap((d) => [d.max, d.min]).filter((v) => v != null);
  const ticks = niceTicks(Math.min(...values) - 1, Math.max(...values) + 1);
  const lo = ticks[0];
  const hi = ticks[ticks.length - 1];
  const step = innerW / Math.max(days.length - 1, 1);
  const x = (i) => PAD.left + i * step;
  const y = (v) => PAD.top + innerH - ((v - lo) / (hi - lo || 1)) * innerH;
  const path = (key) => days.map((d, i) => `${i ? 'L' : 'M'}${x(i)},${y(d[key])}`).join(' ');
  const last = days.length - 1;

  return (
    <div className="relative" onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
        aria-label="Daily maximum and minimum temperature in degrees Celsius">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke={COLORS.grid} strokeWidth="1" />
            <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="13" fill={COLORS.axis}>{t}°</text>
          </g>
        ))}
        {days.map((d, i) => (
          <text key={d.date} x={x(i)} y={H - 8} textAnchor="middle" fontSize="13" fill={COLORS.axis}>{weekday(d.date)}</text>
        ))}
        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + innerH} stroke="#94a3b8" strokeWidth="1" />
        )}
        {['max', 'min'].map((key) => (
          <g key={key}>
            <path d={path(key)} fill="none" stroke={COLORS[key]} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            {days.map((d, i) => (
              <circle key={d.date} cx={x(i)} cy={y(d[key])} r={hover === i ? 5 : 4} fill={COLORS[key]} stroke="#fff" strokeWidth="2" />
            ))}
          </g>
        ))}
        {/* Direct labels at the line ends (identity is not color-only) */}
        <text x={x(last) + 8} y={y(days[last].max) + 4} fontSize="13" fill="#374151">Max</text>
        <text x={x(last) + 8} y={y(days[last].min) + 4} fontSize="13" fill="#374151">Min</text>
        {/* Hit targets: one column per day, wider than the marks */}
        {days.map((d, i) => (
          <rect key={d.date} x={x(i) - step / 2} y={PAD.top} width={step} height={innerH} fill="transparent"
            onPointerEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0}
            aria-label={`${weekday(d.date)}: max ${round(d.max)} °C, min ${round(d.min)} °C`} />
        ))}
      </svg>
      {hover != null && (
        <Tooltip day={days[hover]} x={x(hover)}>
          {[['max', 'Max'], ['min', 'Min']].map(([key, label]) => (
            <p key={key} className="flex items-center gap-2 mt-1 text-slate-600">
              <span className="inline-block w-3 h-0.5 rounded" style={{ background: COLORS[key] }} />
              <strong className="text-slate-900">{round(days[hover][key], 1)} °C</strong> {label}
            </p>
          ))}
        </Tooltip>
      )}
    </div>
  );
}

function RainChart({ days, showChance }) {
  const [hover, setHover] = useState(null);
  const maxRain = Math.max(5, ...days.map((d) => d.rain ?? 0));
  const ticks = niceTicks(0, maxRain, 3);
  const top = ticks[ticks.length - 1];
  const slot = innerW / days.length;
  const barW = Math.min(36, slot * 0.6);
  const y = (v) => PAD.top + innerH - (v / (top || 1)) * innerH;

  return (
    <div className="relative" onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Daily rainfall in millimetres">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke={COLORS.grid} strokeWidth="1" />
            <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="13" fill={COLORS.axis}>{t}</text>
          </g>
        ))}
        {days.map((d, i) => {
          const cx = PAD.left + slot * i + slot / 2;
          const h = Math.max(0, PAD.top + innerH - y(d.rain ?? 0));
          const r = Math.min(4, h / 2);
          const x0 = cx - barW / 2;
          const yTop = PAD.top + innerH - h;
          // Rounded top corners only; the bar stays flat on the baseline
          const shape = h > 0
            ? `M${x0},${PAD.top + innerH} V${yTop + r} Q${x0},${yTop} ${x0 + r},${yTop} H${x0 + barW - r} Q${x0 + barW},${yTop} ${x0 + barW},${yTop + r} V${PAD.top + innerH} Z`
            : null;
          return (
            <g key={d.date}>
              {shape && <path d={shape} fill={COLORS.rain} opacity={hover == null || hover === i ? 1 : 0.55} />}
              <text x={cx} y={H - 8} textAnchor="middle" fontSize="13" fill={COLORS.axis}>{weekday(d.date)}</text>
              <rect x={cx - slot / 2} y={PAD.top} width={slot} height={innerH} fill="transparent" tabIndex={0}
                onPointerEnter={() => setHover(i)} onFocus={() => setHover(i)}
                aria-label={`${weekday(d.date)}: ${round(d.rain, 1)} mm rain`} />
            </g>
          );
        })}
        <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + innerH} y2={PAD.top + innerH} stroke="#9ca3af" strokeWidth="1" />
      </svg>
      {hover != null && (
        <Tooltip day={days[hover]} x={PAD.left + slot * hover + slot / 2}>
          <p className="mt-1 text-slate-600"><strong className="text-slate-900">{round(days[hover].rain, 1)} mm</strong> rain</p>
          {showChance && days[hover].chance != null && (
            <p className="text-slate-600"><strong className="text-slate-900">{days[hover].chance}%</strong> chance of rain</p>
          )}
        </Tooltip>
      )}
    </div>
  );
}

/* ---------- Panel ---------- */

function Stat({ label, value }) {
  return (
    <div className="px-3 py-2 rounded-xl bg-white/70 border border-sky-100">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-bold text-slate-900 tabular-nums">{value}</p>
    </div>
  );
}

export default function WeatherPanel({ location }) {
  // Result for one place: { key: 'lat,lon', data, error }. "Loading" = no result for this place yet.
  const [state, setState] = useState({ key: null, data: null, error: '' });
  const [range, setRange] = useState('next'); // 'next' = forecast week, 'past' = last 7 days
  const [showTable, setShowTable] = useState(false);
  const lat = location?.latitude;
  const lon = location?.longitude;
  const placeKey = lat == null || lon == null ? null : `${lat.toFixed(3)},${lon.toFixed(3)}`;

  useEffect(() => {
    if (!placeKey) return undefined;
    const controller = new AbortController();
    const params = new URLSearchParams({
      latitude: lat.toFixed(3),
      longitude: lon.toFixed(3),
      current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,is_day',
      daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max',
      past_days: '7',
      forecast_days: '7',
      timezone: 'auto',
    });
    fetch(`${API}?${params}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Weather service error ${r.status}`))))
      .then((data) => setState({ key: placeKey, data, error: '' }))
      .catch((err) => {
        if (err.name !== 'AbortError') setState({ key: placeKey, data: null, error: err.message });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [placeKey]);

  const ready = state.key === placeKey;
  const days = useMemo(() => {
    const d = ready ? state.data?.daily : null;
    if (!d) return [];
    return d.time.map((date, i) => ({
      date,
      code: d.weather_code[i],
      max: d.temperature_2m_max[i],
      min: d.temperature_2m_min[i],
      rain: d.precipitation_sum[i],
      chance: d.precipitation_probability_max?.[i],
    }));
  }, [ready, state.data]);

  if (!location) {
    return (
      <div className="p-5 rounded-2xl bg-white border border-slate-200 text-sm text-slate-500">
        Pick your farm on the map to see its current weather and the week ahead.
      </div>
    );
  }
  if (!ready) {
    return (
      <div className="flex items-center gap-3 p-5 rounded-2xl bg-sky-50 border border-sky-200 text-sm text-sky-800">
        <span className="w-4 h-4 rounded-full border-2 border-sky-600 border-t-transparent animate-spin" />
        Loading the weather for {location.placeName?.split(',')[0] || 'your farm'}…
      </div>
    );
  }
  if (state.error || !state.data) {
    return (
      <div className="p-5 rounded-2xl bg-red-50 border border-red-200 text-sm text-red-700" role="alert">
        Weather could not be loaded ({state.error}). Check your internet connection and pick the location again.
      </div>
    );
  }

  const cur = state.data.current;
  const [curText, curIcon] = describe(cur.weather_code, cur.is_day);
  const today = cur.time.slice(0, 10);
  const todayIndex = Math.max(0, days.findIndex((d) => d.date === today));
  const week = range === 'next' ? days.slice(todayIndex, todayIndex + 7) : days.slice(Math.max(0, todayIndex - 7), todayIndex);
  const hot40 = week.filter((d) => d.max >= 40).length;
  const hot35 = week.filter((d) => d.max >= 35).length;
  const frost = week.filter((d) => d.min <= 0).length;
  const wet = week.filter((d) => (d.rain ?? 0) >= 10).length;
  const total = week.reduce((s, d) => s + (d.rain ?? 0), 0);
  const updated = new Date(cur.time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="space-y-5">
      {/* Current weather */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-sky-50 via-white to-emerald-50 border border-sky-200 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Weather now</p>
            <p className="mt-1 text-sm font-semibold text-slate-700">{location.placeName?.split(',').slice(0, 2).join(',')}</p>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-5xl" aria-hidden="true">{curIcon}</span>
              <div>
                <p className="text-4xl font-extrabold text-slate-900 tabular-nums">{round(cur.temperature_2m, 1)}°C</p>
                <p className="text-sm text-slate-600">{curText} · feels like {round(cur.apparent_temperature, 1)}°C</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Humidity" value={`${round(cur.relative_humidity_2m)}%`} />
            <Stat label="Wind" value={`${round(cur.wind_speed_10m)} km/h`} />
            <Stat label="Rain now" value={`${round(cur.precipitation, 1)} mm`} />
            <Stat label="Today" value={`${round(days[todayIndex]?.max)}° / ${round(days[todayIndex]?.min)}°`} />
          </div>
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          Updated {updated} local time · Weather forecast by Open-Meteo (not NASA data). Forecasts can change.
        </p>
      </div>

      {/* Week selector + summary */}
      <div className="p-5 sm:p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex p-1 rounded-xl bg-slate-100" role="group" aria-label="Which week">
            {[['next', 'Next 7 days'], ['past', 'Last 7 days']].map(([key, label]) => (
              <button key={key} type="button" onClick={() => setRange(key)} aria-pressed={range === key}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${range === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
                {label}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setShowTable((v) => !v)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50">
            {showTable ? 'Show charts' : 'Show table'}
          </button>
        </div>

        {/* Day strip */}
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
          {week.map((d) => {
            const [text, icon] = describe(d.code);
            return (
              <div key={d.date} className={`p-2 text-center rounded-xl border ${d.date === today ? 'border-emerald-400 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`} title={text}>
                <p className="text-xs font-semibold text-slate-700">{d.date === today ? 'Today' : weekday(d.date)}</p>
                <p className="text-[10px] text-slate-500">{dayMonth(d.date)}</p>
                <p className="my-1 text-2xl" aria-label={text}>{icon}</p>
                <p className="text-xs font-bold text-slate-900 tabular-nums">{round(d.max)}° <span className="font-normal text-slate-500">{round(d.min)}°</span></p>
                <p className="text-[11px] text-slate-600 tabular-nums">💧 {round(d.rain, 1)} mm</p>
              </div>
            );
          })}
        </div>

        {/* Farm notes from the same thresholds the alerts use */}
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 text-slate-700">
            🌧️ Total rain: <strong className="text-slate-900">{round(total, 1)} mm</strong>
          </span>
          {hot40 > 0 && (
            <span className="px-2.5 py-1 rounded-full border border-red-200 bg-red-50 text-red-700">
              🔥 <strong>{hot40}</strong> day{hot40 > 1 ? 's' : ''} at 40 °C or more
            </span>
          )}
          {hot40 === 0 && hot35 > 0 && (
            <span className="px-2.5 py-1 rounded-full border border-amber-200 bg-amber-50 text-amber-800">
              ☀️ <strong>{hot35}</strong> hot day{hot35 > 1 ? 's' : ''} (35 °C or more)
            </span>
          )}
          {frost > 0 && (
            <span className="px-2.5 py-1 rounded-full border border-sky-200 bg-sky-50 text-sky-800">
              ❄️ <strong>{frost}</strong> frost night{frost > 1 ? 's' : ''} (0 °C or less)
            </span>
          )}
          {wet > 0 && (
            <span className="px-2.5 py-1 rounded-full border border-sky-200 bg-sky-50 text-sky-800">
              ⛈️ <strong>{wet}</strong> heavy-rain day{wet > 1 ? 's' : ''} (10 mm or more)
            </span>
          )}
          {hot35 === 0 && frost === 0 && wet === 0 && (
            <span className="px-2.5 py-1 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-800">
              ✅ No heat, frost or heavy-rain days {range === 'next' ? 'expected' : 'recorded'}
            </span>
          )}
        </div>

        {showTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Daily weather</caption>
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
                  <th className="py-2 pr-3">Day</th><th className="py-2 pr-3">Weather</th>
                  <th className="py-2 pr-3 text-right">Max °C</th><th className="py-2 pr-3 text-right">Min °C</th>
                  <th className="py-2 pr-3 text-right">Rain mm</th>
                  {range === 'next' && <th className="py-2 text-right">Rain chance</th>}
                </tr>
              </thead>
              <tbody>
                {week.map((d) => (
                  <tr key={d.date} className="border-b border-slate-100 tabular-nums">
                    <td className="py-2 pr-3 font-medium text-slate-900">{weekday(d.date)} {dayMonth(d.date)}</td>
                    <td className="py-2 pr-3 text-slate-700">{describe(d.code)[0]}</td>
                    <td className="py-2 pr-3 text-right">{round(d.max, 1)}</td>
                    <td className="py-2 pr-3 text-right">{round(d.min, 1)}</td>
                    <td className="py-2 pr-3 text-right">{round(d.rain, 1)}</td>
                    {range === 'next' && <td className="py-2 text-right">{d.chance == null ? '—' : `${d.chance}%`}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-900">Temperature (°C)</p>
                <div className="flex items-center gap-3 text-xs text-slate-600">
                  <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-0.5 rounded" style={{ background: COLORS.max }} />Max</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-0.5 rounded" style={{ background: COLORS.min }} />Min</span>
                </div>
              </div>
              {week.length > 1 && <TemperatureChart days={week} />}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Rainfall (mm per day)</p>
              {week.length > 0 && <RainChart days={week} showChance={range === 'next'} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
