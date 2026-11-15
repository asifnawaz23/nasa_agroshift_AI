import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import Footer from '../components/Footer';
import mainLogo from '../assets/mainLogo.jpg';
import member1 from '../assets/team/member1.png';
import member2 from '../assets/team/member2.webp';
import member3 from '../assets/team/member3.jpeg';
import member4 from '../assets/team/member4.png';
import member5 from '../assets/team/member5.webp';
import member6 from '../assets/team/member6.webp';
import './Dashboard.css';

/* ---------- Content (from the team plan: FIELD_SHIFT_TEAM_PLAN.md) ---------- */

const STEPS = [
  { title: 'Pick your field', text: 'Search, use GPS, or tap any point on the satellite map.' },
  { title: 'Tell us about it', text: 'Current crop, water availability and what matters most to you.' },
  { title: 'We analyze', text: '20 years of NASA climate data plus soil data for your exact location.' },
  { title: 'Decide with confidence', text: 'Compare strategies, read the risk alerts, and ask the assistant.' },
];

const DATA_SOURCES = [
  { name: 'NASA POWER', what: 'Daily rainfall, temperature, sunlight and humidity for any point on Earth, going back decades.', status: 'used', note: 'Every analysis' },
  { name: 'SMAP', what: 'Satellite soil-moisture measurements (since 2015) — shows dry spells in the root zone.', status: 'used', note: 'Featured locations' },
  { name: 'MODIS NDVI', what: 'Daily vegetation greenness at 250 m–1 km — shows when fields are green or bare.', status: 'used', note: 'Featured locations' },
  { name: 'ISRIC SoilGrids', what: 'Global soil maps: sand, silt, clay, organic carbon and pH (non-NASA).', status: 'used', note: 'Every analysis' },
  { name: 'GPM / IMERG', what: 'Satellite rainfall estimates every 30 minutes across the globe.', status: 'planned', note: 'Planned' },
  { name: 'Landsat', what: '30 m images of land and vegetation, continuous since 1972 — field-level detail.', status: 'planned', note: 'Future work' },
  { name: 'ECOSTRESS', what: 'Plant heat stress and evapotranspiration measured from the Space Station.', status: 'planned', note: 'Future work' },
];

// To fix who is in which photo, just swap the `photo` values below.
// Optional `zoom` + `focus` (x% y% of the face) zoom wide shots in so every card shows a portrait.
const TEAM = [
  { name: 'Shayan Khan', team: 'Backend', role: 'Tech lead — API, scoring, AI endpoints', photo: member1 },
  { name: 'Asif Nawaz', team: 'Backend', role: 'Climate engine, What-If scenarios, alerts', photo: member5, zoom: 1.7, focus: '50% 47%' },
  { name: 'Aman Ullah', team: 'Backend', role: 'NASA data sources, caching, AI client', photo: member3 },
  { name: 'Abdul Rehman', team: 'Backend', role: 'Crop knowledge base, ground data, tests', photo: member6 },
  { name: 'Talha Ikram', team: 'Frontend', role: 'Frontend lead — app, map, chat', photo: member4 },
  { name: 'Ahmed Musab', team: 'Frontend', role: 'Charts, polish, story and slides', photo: member2, zoom: 1.35, focus: '50% 28%' },
];

/* ---------- Small building blocks ---------- */

function SectionTitle({ eyebrow, title, text }) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-semibold tracking-[0.18em] text-green-700 uppercase">{eyebrow}</p>
      <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">{title}</h2>
      {text && <p className="mt-2 text-slate-600">{text}</p>}
    </div>
  );
}

function AboutContent({ isLoggedIn }) {
  return (
    <div className="space-y-16">
      {/* ---------- Hero ---------- */}
      <section className="dash-hero dash-rise rounded-3xl px-6 py-10 sm:px-12 sm:py-14 text-white shadow-xl shadow-slate-900/20">
        <div className="dash-orbit" aria-hidden="true" />
        <div className="dash-globe" aria-hidden="true" />
        <div className="relative max-w-2xl">
          <p className="text-[11px] font-mono tracking-[0.22em] text-sky-300 uppercase">
            NASA Space Apps Challenge 2026
          </p>
          <h1 className="mt-3 text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight">
            Helping farmers adapt with <span className="dash-gradient-text">NASA Earth data</span>
          </h1>
          <p className="mt-4 text-base sm:text-lg text-white/75">
            AgroShift AI turns satellite and climate data into clear, practical crop-rotation advice —
            so every farmer can plan the season ahead with the same data scientists use.
          </p>
          <p className="mt-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs font-semibold">
            🏆 Challenge: <span className="text-amber-300">Field Shift — Adapting Farms with NASA Data</span>
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to={isLoggedIn ? '/' : '/signup'}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-bold text-slate-900 bg-gradient-to-b from-amber-200 via-amber-400 to-orange-500 shadow-[inset_0_1px_0_rgba(255,255,255,.6),0_5px_0_#a8621a] active:translate-y-1 active:shadow-[0_1px_0_#a8621a] transition"
            >
              {isLoggedIn ? 'Go to my dashboard' : 'Get started free'} <span aria-hidden="true">→</span>
            </Link>
            <a
              href="#about-data"
              className="inline-flex items-center px-5 py-3 rounded-xl text-sm font-semibold text-white bg-white/10 border border-white/20 hover:bg-white/15 transition"
            >
              Our data sources
            </a>
          </div>
        </div>
      </section>

      {/* ---------- Mission ---------- */}
      <section className="max-w-3xl">
        <SectionTitle
          eyebrow="Our mission"
          title="Climate is changing faster than farming advice"
          text="Satellite data shows these shifts clearly, but it is usually locked away in scientific tools. We bring it to the field — built first for farmers in Punjab and Sindh, and working for any point on Earth."
        />
      </section>

      {/* ---------- How it works ---------- */}
      <section className="space-y-8">
        <SectionTitle eyebrow="How it works" title="From a dot on the map to a decision" />
        <ol className="grid gap-4 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative p-6 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-green-500 to-emerald-700 text-white font-bold shadow-md shadow-green-600/30">
                {i + 1}
              </span>
              <h3 className="mt-4 font-bold text-slate-900">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ---------- About the data ---------- */}
      <section id="about-data" className="scroll-mt-24 space-y-8">
        <SectionTitle eyebrow="About the data" title="The data behind every answer" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {DATA_SOURCES.filter((d) => d.status === 'used').map((d) => (
            <div key={d.name} className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <h3 className="font-bold text-slate-900">{d.name}</h3>
              <p className="mt-1 text-sm text-slate-600 leading-relaxed">{d.what}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-slate-500">
          Planned next:{' '}
          {DATA_SOURCES.filter((d) => d.status === 'planned').map((d) => d.name).join(', ')}.
        </p>
      </section>

      {/* ---------- Team ---------- */}
      <section className="space-y-8">
        <SectionTitle eyebrow="The team" title="Built in 24 hours by six people" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TEAM.map((m) => (
            <figure
              key={m.name}
              className="dash-card group overflow-hidden bg-white border border-slate-200 rounded-3xl shadow-sm"
            >
              <div className="relative aspect-[4/5] overflow-hidden bg-slate-100">
                {m.photo ? (
                  // Outer layer: per-photo zoom on the face; inner image: hover zoom
                  <div
                    className="w-full h-full"
                    style={{ transform: `scale(${m.zoom ?? 1})`, transformOrigin: m.focus ?? '50% 20%' }}
                  >
                    <img
                      src={m.photo}
                      alt={`${m.name}, ${m.team} developer`}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      style={{ objectPosition: m.focus ?? '50% 20%' }}
                    />
                  </div>
                ) : (
                  <span className="flex items-center justify-center w-full h-full text-5xl font-extrabold text-slate-300">
                    {m.name[0]}
                  </span>
                )}
                {/* Soft fade so the badge stays readable on any photo */}
                <span className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-black/45 to-transparent" aria-hidden="true" />
                <span
                  className={`absolute left-4 bottom-4 px-2.5 py-1 text-[11px] font-bold tracking-wide uppercase rounded-full text-white shadow ${
                    m.team === 'Backend'
                      ? 'bg-gradient-to-r from-sky-500 to-indigo-600'
                      : 'bg-gradient-to-r from-amber-500 to-green-600'
                  }`}
                >
                  {m.team}
                </span>
              </div>
              <figcaption className="p-5">
                <p className="text-lg font-bold text-slate-900">{m.name}</p>
                <p className="mt-1 text-sm text-slate-600">{m.role}</p>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* ---------- Credits ---------- */}
      <p className="text-xs text-slate-500 text-center">
        Data: NASA POWER, SMAP and MODIS (NASA) · ISRIC SoilGrids · USDA SSURGO & CDL · PRISM · FAO.
        Map imagery © Esri and © OpenStreetMap contributors.
      </p>
    </div>
  );
}

/* ---------- Page ---------- */

export default function About() {
  const isLoggedIn = useSelector((s) => s.auth.isAuthenticated);
  const navigate = useNavigate();

  // Links like /about#about-data: scroll to that part of the page (or the top otherwise)
  const { hash } = useLocation();
  useEffect(() => {
    const target = hash ? document.getElementById(hash.slice(1)) : null;
    if (target) setTimeout(() => target.scrollIntoView({ block: 'start' }), 100);
    else window.scrollTo(0, 0);
  }, [hash]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Same minimized-sidebar preference as the dashboard
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('sidebarCollapsed') === 'true';
    } catch {
      return false;
    }
  });
  const toggleCollapsed = () =>
    setCollapsed((c) => {
      try {
        localStorage.setItem('sidebarCollapsed', String(!c));
      } catch {
        /* storage unavailable — ignore */
      }
      return !c;
    });

  // Logged in: same app layout as the dashboard
  if (isLoggedIn) {
    return (
      <div className="min-h-screen flex bg-gradient-to-br from-slate-50 via-white to-emerald-50/40">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          activeId="about"
          onNavigate={(id) => navigate('/', { state: { scrollTo: id } })}
          collapsed={collapsed}
          onToggleCollapse={toggleCollapsed}
        />
        <div className="flex-1 flex flex-col min-w-0">
          <Header title="About Us" onMenuClick={() => setSidebarOpen(true)} />
          <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-8 py-6 sm:py-8">
            <AboutContent isLoggedIn />
          </main>
          <Footer />
        </div>
      </div>
    );
  }

  // Visitors: simple top bar
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 via-white to-emerald-50/40">
      <header className="sticky top-0 z-20 bg-white/80 backdrop-blur-xl border-b border-slate-200/70">
        <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4 sm:px-8">
          <Link to="/" className="flex items-center gap-2.5 font-extrabold text-slate-900">
            <img src={mainLogo} alt="" className="w-9 h-9 p-1 rounded-xl bg-white object-contain ring-1 ring-slate-200" />
            AgroShift AI
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/login" className="px-4 py-2 text-sm font-semibold text-slate-700 rounded-xl hover:bg-slate-100">
              Sign in
            </Link>
            <Link to="/signup" className="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-xl hover:bg-green-700">
              Get started
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-8 py-8">
        <AboutContent isLoggedIn={false} />
      </main>
      <Footer />
    </div>
  );
}
