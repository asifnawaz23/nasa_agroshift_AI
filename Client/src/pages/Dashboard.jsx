import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { NAV_ITEMS } from '../components/navItems';
import Header from '../components/Header';
import Footer from '../components/Footer';
import FarmMap from '../components/FarmMap';
import FarmerInputForm from '../components/FarmerInputForm';
import Charts from '../components/Charts';
import { mockAnalysis } from '../data/mockAnalysis';
import { analyzeFarm, explainAnalysis } from '../services/api';
import ChatPanel from '../components/ChatPanel';
import ExplanationCard from '../components/ExplanationCard';
import WhatIfPanel from '../components/WhatIfPanel';
import './Dashboard.css';

/* ---------- Small building blocks ---------- */

// Small coloured chip shown next to a section title (e.g. "✓ Selected", "Required")
const CHIP_TONES = {
  done: 'bg-green-50 text-green-700 border-green-200',
  todo: 'bg-amber-50 text-amber-800 border-amber-200',
  info: 'bg-sky-50 text-sky-700 border-sky-200',
  muted: 'bg-slate-50 text-slate-500 border-slate-200',
};

function Section({ id, step, title, subtitle, status, children }) {
  return (
    <section id={id} className="scroll-mt-24 dash-rise">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-green-500 to-emerald-700 text-white text-sm font-bold shadow-md shadow-green-600/30">
            {step}
          </span>
          <div>
            <h2 className="text-lg font-bold text-slate-900">{title}</h2>
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {status && (
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${CHIP_TONES[status.tone]}`}>
            {status.text}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

function StatCard({ label, value, hint, icon, tone = 'green', example = false, empty = false }) {
  const tones = {
    green: { icon: 'from-green-500/15 to-emerald-500/5 text-green-700', bar: 'from-green-400 to-emerald-600' },
    blue: { icon: 'from-sky-500/15 to-blue-500/5 text-sky-700', bar: 'from-sky-400 to-blue-600' },
    amber: { icon: 'from-amber-400/20 to-orange-400/5 text-amber-700', bar: 'from-amber-300 to-orange-500' },
    violet: { icon: 'from-violet-500/15 to-indigo-500/5 text-violet-700', bar: 'from-violet-400 to-indigo-600' },
  };
  return (
    <div
      className={`dash-card relative overflow-hidden p-5 bg-white border rounded-2xl shadow-sm ${
        example ? 'border-amber-300 border-dashed' : 'border-slate-200/80'
      }`}
    >
      {/* Coloured accent strip */}
      <span
        className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${tones[tone].bar} ${empty ? 'opacity-30' : ''}`}
        aria-hidden="true"
      />
      {example && (
        <span className="absolute top-2 right-2 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-amber-800 bg-amber-100 rounded uppercase">
          Example
        </span>
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{label}</p>
          <p
            className={`mt-2 text-xl font-bold truncate ${empty ? 'text-slate-300' : 'text-slate-900'}`}
            title={typeof value === 'string' ? value : undefined}
          >
            {value}
          </p>
          {hint && <p className="mt-1 text-xs text-slate-500 truncate">{hint}</p>}
        </div>
        <span
          className={`shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br text-2xl ring-1 ring-black/5 ${tones[tone].icon}`}
        >
          {icon}
        </span>
      </div>
    </div>
  );
}

/* Progress through the 3 steps, shown in the welcome banner */
function ProgressTracker({ steps, onStepClick }) {
  const doneCount = steps.filter((s) => s.done).length;
  const current = steps.findIndex((s) => !s.done);
  return (
    <div className="mt-6 max-w-lg">
      <div className="flex items-center justify-between text-xs font-semibold">
        <span className="text-white/80">
          {doneCount === steps.length ? 'All steps complete 🎉' : `Step ${current + 1} of ${steps.length}`}
        </span>
        <span className="text-amber-300">{Math.round((doneCount / steps.length) * 100)}%</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-amber-300 via-green-400 to-emerald-500 transition-all duration-700"
          style={{ width: `${(doneCount / steps.length) * 100}%` }}
        />
      </div>
      <ol className="mt-3 grid grid-cols-3 gap-2">
        {steps.map((s, i) => (
          <li key={s.label}>
            <button
              type="button"
              onClick={() => onStepClick(s.target)}
              className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-xl text-left text-xs font-semibold border backdrop-blur transition
                ${s.done
                  ? 'bg-green-400/15 border-green-300/30 text-green-100'
                  : i === current
                    ? 'bg-white/15 border-white/30 text-white'
                    : 'bg-white/5 border-white/10 text-white/50 hover:text-white/80'}`}
            >
              <span
                className={`flex items-center justify-center w-5 h-5 shrink-0 rounded-full text-[10px] font-bold
                  ${s.done ? 'bg-green-400 text-green-950' : 'bg-white/20 text-white'}`}
              >
                {s.done ? '✓' : i + 1}
              </span>
              <span className="truncate">{s.label}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}

const DATA_BADGES = [
  { name: 'NASA POWER', text: 'Climate' },
  { name: 'SMAP', text: 'Soil moisture' },
  { name: 'MODIS NDVI', text: 'Vegetation' },
  { name: 'SoilGrids', text: 'Soil' },
];

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

/* ---------- Page ---------- */

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Desktop minimize — remembered in this browser
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('sidebarCollapsed') === 'true';
    } catch {
      return false;
    }
  });
  const toggleCollapsed = () => {
    setCollapsed((c) => {
      try {
        localStorage.setItem('sidebarCollapsed', String(!c));
      } catch {
        /* storage unavailable — ignore */
      }
      return !c;
    });
  };
  const [activeId, setActiveId] = useState('overview');
  const [farmLocation, setFarmLocation] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  // The farmer's real analysis (POST /api/analyze/) — null until they run one.
  // Sample data is only shown when they ask for it, and is always labelled "Example".
  const [analysis, setAnalysis] = useState(null);
  const [showExample, setShowExample] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');
  const [explanation, setExplanation] = useState(null);
  // What-If: the last request body, today's result, and the simulated result
  const [basePayload, setBasePayload] = useState(null);
  const [baselineAnalysis, setBaselineAnalysis] = useState(null);
  const [scenarioAnalysis, setScenarioAnalysis] = useState(null);
  // Which analysis the explanation being fetched belongs to (drops late answers for old farms)
  const explainFor = useRef(null);

  const user = useSelector((s) => s.auth.user);
  const email = user?.email ?? '';
  const name = user?.full_name?.split(' ')[0] || (email ? email.split('@')[0] : 'Farmer');

  // What the cards and charts display: your real results, else the example (if opened), else nothing
  const shown = analysis ?? (showExample ? mockAnalysis : null);
  const isExample = !analysis && showExample;

  const strategies = shown?.strategies ?? [];
  const best = strategies.reduce(
    (a, b) => (b.scores.overall > (a?.scores.overall ?? -1) ? b : a),
    null
  );
  const current = strategies.find((s) => s.key === 'current');
  // Backend scores can be decimals — round to 1 place to avoid 1.7000000000000028
  const gain = best && current ? Math.round((best.scores.overall - current.scores.overall) * 10) / 10 : 0;

  // Highlight the sidebar item for the section in view
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((e) => e.isIntersecting);
        if (visible) setActiveId(visible.target.id);
      },
      { rootMargin: '-30% 0px -60% 0px' }
    );
    NAV_ITEMS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const goTo = (id) => {
    setActiveId(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Coming back from another page (e.g. About Us → "Analysis"): scroll to that section
  const routerLocation = useLocation();
  const scrollTarget = routerLocation.state?.scrollTo;
  useEffect(() => {
    if (!scrollTarget) return;
    // Jump (not smooth-scroll) on arrival: the page is still loading, which can cut a smooth scroll short
    const t = setTimeout(() => {
      setActiveId(scrollTarget);
      document.getElementById(scrollTarget)?.scrollIntoView({ block: 'start' });
    }, 150);
    return () => clearTimeout(t);
  }, [scrollTarget]);

  const handleFarmSubmit = async (farmData) => {
    setAnalyzing(true);
    setAnalyzeError('');
    setExplanation(null);
    goTo('analysis');

    try {
      // 1) POST /api/analyze/ -> strategies, climate, soil, alerts...
      const result = await analyzeFarm(farmData);
      setAnalysis(result);
      setShowExample(false); // real results replace the example
      setBasePayload(farmData);
      setBaselineAnalysis(result);
      setScenarioAnalysis(null);
      setSubmitted(true);
      // Show scores and alerts right away; the explanation arrives a few seconds later
      setAnalyzing(false);

      // 2) POST /api/explain/ -> plain-language summary of the best strategy (in the background)
      explainFor.current = result.analysis_id;
      explainAnalysis(result, farmData.lang)
        .then((e) => {
          if (explainFor.current === result.analysis_id) setExplanation(e);
        })
        .catch(() => {
          /* explanation is optional — charts still show */
        });
    } catch (err) {
      setAnalyzeError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // Called by the What-If sliders (debounced). `isLatest` drops answers to older slider moves.
  const runScenario = async (scenario, isLatest) => {
    const result = await analyzeFarm({ ...basePayload, scenario });
    if (!isLatest()) return;
    setScenarioAnalysis(result);
    setAnalysis(result);
  };
  const resetScenario = () => {
    setScenarioAnalysis(null);
    if (baselineAnalysis) setAnalysis(baselineAnalysis);
  };
  const simulated = !!scenarioAnalysis;

  const activeLabel = NAV_ITEMS.find((n) => n.id === activeId)?.label ?? 'Overview';

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-slate-50 via-white to-emerald-50/40">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeId={activeId}
        onNavigate={goTo}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header title={activeLabel} onMenuClick={() => setSidebarOpen(true)} />

        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-8 py-6 sm:py-8 space-y-10">
          {/* ---------- Overview ---------- */}
          <section id="overview" className="scroll-mt-24 space-y-6">
            <div className="dash-hero dash-rise rounded-3xl px-6 py-8 sm:px-10 sm:py-10 text-white shadow-xl shadow-slate-900/20">
              <div className="dash-orbit" aria-hidden="true" />
              <div className="dash-globe" aria-hidden="true" />

              <div className="relative max-w-xl">
                <p className="text-[11px] font-mono tracking-[0.22em] text-sky-300 uppercase">
                  Earth data · Smarter farms
                </p>
                <h1 className="mt-3 text-3xl sm:text-4xl font-extrabold tracking-tight">
                  {greeting()}, <span className="dash-gradient-text capitalize">{name}</span> 👋
                </h1>
                <p className="mt-3 text-sm sm:text-base text-white/70">
                  Pick your field, tell us about it, and let satellite data find the
                  best crop rotation for you.
                </p>

                <ProgressTracker
                  onStepClick={goTo}
                  steps={[
                    { label: 'Location', done: !!farmLocation, target: 'location' },
                    { label: 'Farm details', done: submitted, target: 'details' },
                    { label: 'Results', done: !!analysis, target: 'analysis' },
                  ]}
                />

                <button
                  type="button"
                  onClick={() => goTo(farmLocation ? 'details' : 'location')}
                  className="mt-7 inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-bold text-slate-900 bg-gradient-to-b from-amber-200 via-amber-400 to-orange-500 shadow-[inset_0_1px_0_rgba(255,255,255,.6),0_5px_0_#a8621a,0_14px_24px_-8px_rgba(232,145,42,.7)] active:translate-y-1 active:shadow-[0_1px_0_#a8621a] transition"
                >
                  {submitted ? 'Update my farm' : farmLocation ? 'Add farm details' : 'Start with your location'}
                  <span aria-hidden="true">→</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Farm location"
                value={farmLocation ? farmLocation.placeName.split(',')[0] : 'Not selected'}
                hint={
                  farmLocation
                    ? `${farmLocation.latitude.toFixed(3)}, ${farmLocation.longitude.toFixed(3)}`
                    : 'Pick it on the map below'
                }
                icon="📍"
                tone="green"
              />
              <StatCard
                label="Best strategy"
                value={best?.name ?? '—'}
                hint={best ? `Overall score ${best.scores.overall}/100` : 'Run an analysis to see this'}
                icon="🌱"
                tone="amber"
                example={isExample}
                empty={!best}
              />
              <StatCard
                label="Potential gain"
                value={shown ? (gain > 0 ? `+${gain} pts` : 'No gain') : '—'}
                hint={shown ? 'vs your current rotation' : 'Run an analysis to see this'}
                icon="📈"
                tone="blue"
                example={isExample}
                empty={!shown}
              />
              <StatCard
                label="Data status"
                value={
                  analysis
                    ? analysis.data_quality?.status === 'complete'
                      ? 'Live analysis'
                      : 'Partial data'
                    : isExample
                      ? 'Example data'
                      : 'No analysis yet'
                }
                hint={(shown?.data_quality?.sources ?? ['NASA POWER', 'SoilGrids']).join(' · ')}
                icon="🛰️"
                tone="violet"
                example={isExample}
                empty={!shown}
              />
            </div>

            {/* Data sources strip */}
            <div className="flex flex-wrap items-center gap-2 px-4 py-3 rounded-2xl bg-white/70 border border-slate-200/80">
              <span className="me-1 text-xs font-semibold tracking-wide text-slate-500 uppercase">Powered by</span>
              {DATA_BADGES.map((d) => (
                <span
                  key={d.name}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-full bg-slate-50 border border-slate-200"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" aria-hidden="true" />
                  <span className="font-semibold text-slate-800">{d.name}</span>
                  <span className="text-slate-500">{d.text}</span>
                </span>
              ))}
              <Link to="/about#about-data" className="ms-auto text-xs font-semibold text-green-700 hover:underline">
                About the data →
              </Link>
            </div>
          </section>

          {/* ---------- Location + Details (side by side on large screens) ---------- */}
          <div className="grid grid-cols-1 gap-10 xl:grid-cols-2 xl:gap-8 xl:items-start">
            <Section
              id="location"
              step="1"
              title="Farm location"
              subtitle="Search, use GPS, or click on the map"
              status={farmLocation ? { tone: 'done', text: '✓ Selected' } : { tone: 'todo', text: 'Required' }}
            >
              {/* `isolate` keeps Leaflet's high z-index map layers under the sticky header */}
              <div className="isolate">
                <FarmMap onLocationSelect={setFarmLocation} />
              </div>
            </Section>

            <Section
              id="details"
              step="2"
              title="Farm details"
              subtitle="A few quick questions about your field"
              status={
                submitted
                  ? { tone: 'done', text: '✓ Submitted' }
                  : farmLocation
                    ? { tone: 'todo', text: 'Next step' }
                    : { tone: 'muted', text: 'Pick a location first' }
              }
            >
              <FarmerInputForm location={farmLocation} onSubmit={handleFarmSubmit} />
            </Section>
          </div>

          {/* ---------- Analysis ---------- */}
          <Section
            id="analysis"
            step="3"
            title="Rotation analysis"
            subtitle="How each strategy scores for your farm"
            status={
              analyzing
                ? { tone: 'info', text: '⏳ Analyzing…' }
                : analysis
                  ? { tone: 'done', text: '✓ Live results' }
                  : isExample
                    ? { tone: 'todo', text: 'Example' }
                    : { tone: 'muted', text: 'Waiting for your farm' }
            }
          >
            <div className="space-y-4">
              {analyzing && (
                <div className="flex items-center gap-3 p-4 rounded-2xl bg-sky-50 border border-sky-200 text-sm text-sky-800">
                  <span className="w-4 h-4 rounded-full border-2 border-sky-600 border-t-transparent animate-spin" />
                  Analyzing your farm with NASA POWER and SoilGrids data… this can take a few seconds.
                </div>
              )}

              {analyzeError && (
                <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-sm text-red-700" role="alert">
                  <p className="font-semibold">Analysis failed</p>
                  <p className="mt-1">{analyzeError}</p>
                </div>
              )}

              {/* POST /api/explain/ result */}
              {/* `key` resets the saved translations when a new analysis comes in */}
              {explanation && (
                <ExplanationCard
                  key={baselineAnalysis?.analysis_id}
                  analysis={baselineAnalysis ?? analysis}
                  initial={explanation}
                />
              )}

              {/* Alerts from the analysis: { severity_label, reason, action, month, crops, ... } */}
              {analysis?.alerts?.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-semibold text-slate-900">
                    ⚠️ Risk alerts for your current rotation
                    <span className={`ml-2 px-2 py-0.5 text-[11px] font-bold rounded-full border ${simulated ? 'bg-violet-100 text-violet-800 border-violet-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                      {simulated ? 'SIMULATED' : 'HISTORICAL (2006–2025)'}
                    </span>
                  </p>
                  <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                    {analysis.alerts.map((a, i) => {
                      const level = (a.severity || '').toLowerCase();
                      const tone =
                        level === 'critical'
                          ? 'border-red-200 bg-red-50 text-red-700'
                          : level === 'warning' || level === 'serious'
                            ? 'border-amber-200 bg-amber-50 text-amber-800'
                            : 'border-sky-200 bg-sky-50 text-sky-800';
                      return (
                        <div key={i} className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`px-2 py-0.5 text-[11px] font-semibold rounded-full border ${tone}`}>
                              {a.severity_label || a.severity || 'Alert'}
                            </span>
                            {a.type && (
                              <span className="text-xs font-medium text-slate-500 capitalize">
                                {String(a.type).replace(/_/g, ' ')}
                              </span>
                            )}
                          </div>
                          <p className="mt-2 text-sm text-slate-800">{a.reason || a.message || a.title}</p>
                          {a.action && (
                            <p className="mt-2 text-sm text-emerald-800">
                              <span className="font-semibold">What to do: </span>
                              {a.action}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Data quality warnings */}
              {analysis?.data_quality?.warnings?.length > 0 && (
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Data notes</p>
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-600 space-y-0.5">
                    {analysis.data_quality.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Example banner — makes it impossible to mistake sample numbers for your farm */}
              {isExample && (
                <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl bg-amber-50 border-2 border-dashed border-amber-300">
                  <p className="text-sm text-amber-900">
                    <span className="font-bold">EXAMPLE — not your farm.</span> These are sample numbers
                    to show what the analysis looks like.
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowExample(false)}
                      className="px-3 py-1.5 text-xs font-semibold text-amber-900 bg-white border border-amber-300 rounded-lg hover:bg-amber-100"
                    >
                      Clear example
                    </button>
                    <button
                      type="button"
                      onClick={() => goTo(farmLocation ? 'details' : 'location')}
                      className="px-3 py-1.5 text-xs font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700"
                    >
                      Analyze my farm
                    </button>
                  </div>
                </div>
              )}

              {shown ? (
                <Charts analysis={shown} />
              ) : (
                !analyzing && (
                  /* Empty state: no fake numbers before the farmer runs an analysis */
                  <div className="p-8 text-center bg-white border-2 border-dashed border-slate-200 rounded-2xl">
                    <span className="text-4xl" aria-hidden="true">🌾</span>
                    <h3 className="mt-3 text-lg font-bold text-slate-900">Your results will appear here</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      We compare crop-rotation strategies for your exact field using NASA climate and soil data.
                    </p>

                    <ol className="mt-6 grid gap-3 text-left sm:grid-cols-3 max-w-2xl mx-auto">
                      {[
                        ['1', 'Pick your farm', farmLocation ? 'Done ✓' : 'Search or click on the map'],
                        ['2', 'Add farm details', 'Crop, water and your main goal'],
                        ['3', 'Analyze', 'Scores, risk alerts and advice'],
                      ].map(([n, title, text]) => (
                        <li key={n} className="flex gap-3 p-3 rounded-xl bg-slate-50">
                          <span className="flex items-center justify-center w-7 h-7 shrink-0 rounded-lg bg-green-600 text-white text-sm font-bold">
                            {n}
                          </span>
                          <div>
                            <p className="text-sm font-semibold text-slate-800">{title}</p>
                            <p className="text-xs text-slate-500">{text}</p>
                          </div>
                        </li>
                      ))}
                    </ol>

                    <div className="mt-6 flex flex-wrap justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => goTo(farmLocation ? 'details' : 'location')}
                        className="px-5 py-2.5 text-sm font-semibold text-white bg-green-600 rounded-xl hover:bg-green-700"
                      >
                        {farmLocation ? 'Add farm details →' : 'Start with your location →'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowExample(true)}
                        className="px-5 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50"
                      >
                        See an example
                      </button>
                    </div>
                  </div>
                )
              )}

              {analysis?.disclaimer && (
                <p className="text-xs text-slate-500">{analysis.disclaimer}</p>
              )}
            </div>
          </Section>

          {/* ---------- What-If (scenario re-run of /api/analyze/) ---------- */}
          <Section
            id="whatif"
            step="4"
            title="What if the climate changes?"
            subtitle="Test a hotter or drier future for your farm"
          >
            <WhatIfPanel
              key={baselineAnalysis?.analysis_id ?? 'none'}
              basePayload={basePayload}
              baselineAnalysis={baselineAnalysis}
              scenarioAnalysis={scenarioAnalysis}
              onRun={runScenario}
              onReset={resetScenario}
            />
          </Section>

          {/* ---------- AI Assistant (POST /api/chat/) ---------- */}
          <Section
            id="assistant"
            step="5"
            title="Farm assistant"
            subtitle="Ask about crops or your analysis"
            status={{ tone: 'info', text: 'EN · اردو · سنڌي · پنجابی' }}
          >
            {/* Only real results go to the assistant — never the example */}
            <ChatPanel analysis={analysis} />
          </Section>

        </main>

        <Footer />
      </div>
    </div>
  );
}
