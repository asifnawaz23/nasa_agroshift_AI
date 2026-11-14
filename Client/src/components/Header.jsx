import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import ProfileModal from './ProfileModal';
import { getHealth } from '../services/api';

/*
  Dashboard top bar.
  Props:
    title       – current section name
    onMenuClick – opens the mobile sidebar
*/
export default function Header({ title, onMenuClick }) {
  const email = useSelector((s) => s.auth.user?.email) ?? 'farmer';
  const [profileOpen, setProfileOpen] = useState(false);

  // GET /api/health/ -> is the backend reachable? (re-checked every 30 s)
  const [online, setOnline] = useState(null); // null = checking
  useEffect(() => {
    const check = () =>
      getHealth()
        .then(() => setOnline(true))
        .catch(() => setOnline(false));
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 h-16 px-4 sm:px-8 bg-white/75 backdrop-blur-xl border-b border-slate-200/70">
      <div className="flex items-center gap-3 min-w-0">
        <button
          className="lg:hidden p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-100"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <nav className="flex items-center gap-2 text-sm min-w-0" aria-label="Breadcrumb">
          <span className="text-slate-400 hidden sm:inline">Dashboard</span>
          <span className="text-slate-300 hidden sm:inline">/</span>
          <span className="font-semibold text-slate-900 truncate">{title}</span>
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
            online === false
              ? 'bg-red-50 border-red-200 text-red-700'
              : online
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-slate-50 border-slate-200 text-slate-500'
          }`}
          title={online === false ? 'Backend not reachable — run python manage.py runserver' : undefined}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              online === false ? 'bg-red-500' : online ? 'dash-ping bg-emerald-500' : 'bg-slate-400'
            }`}
          />
          {online === false ? 'Backend offline' : online ? 'Live Earth data' : 'Connecting…'}
        </div>
        <div className="relative hidden sm:block">
          <svg viewBox="0 0 24 24" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="search"
            placeholder="Search…"
            aria-label="Search"
            className="w-56 pl-9 pr-3 py-2 text-sm bg-slate-100 border border-transparent rounded-xl focus:bg-white focus:border-green-500 focus:ring-2 focus:ring-green-500/20 focus:outline-none transition"
          />
        </div>
        <button
          type="button"
          onClick={() => setProfileOpen(true)}
          className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-300 to-green-500 text-slate-900 flex items-center justify-center font-bold text-sm uppercase ring-2 ring-white shadow hover:ring-green-300 transition"
          title="View profile"
          aria-label="View profile"
        >
          {email[0]}
        </button>
      </div>

      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </header>
  );
}
