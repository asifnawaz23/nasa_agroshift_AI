import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '../features/auth/authSlice';
import mainLogo from '../assets/mainLogo.jpg';
import { NAV_ITEMS, icon } from './navItems';

/*
  Dashboard sidebar.
  Props:
    open      – mobile drawer open?
    onClose   – close the mobile drawer
    activeId  – id of the active nav item
    onNavigate(id) – called when a nav item is clicked
    collapsed – desktop: show icons only?
    onToggleCollapse – minimize / expand (desktop)
*/

export default function Sidebar({
  open,
  onClose,
  activeId,
  onNavigate,
  collapsed = false,
  onToggleCollapse,
}) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const email = useSelector((s) => s.auth.user?.email) ?? 'farmer';

  // On desktop, hide text when minimized. The mobile drawer always shows everything.
  const hideWhenMin = collapsed ? 'lg:hidden' : '';

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
  };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 z-30 bg-black/50 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`dash-sidebar fixed inset-y-0 left-0 z-40 w-72 flex flex-col text-white
          transition-[transform,width] duration-300 ease-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0
          ${collapsed ? 'lg:w-20' : 'lg:w-72'}
          ${open ? 'translate-x-0' : '-translate-x-full'}`}
        aria-label="Main navigation"
      >
        {/* Minimize / expand (desktop only) */}
        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden lg:flex absolute -right-3 top-7 z-10 w-6 h-6 items-center justify-center rounded-full bg-white text-slate-700 shadow-md ring-1 ring-slate-200 hover:bg-green-50 hover:text-green-700 transition"
          aria-label={collapsed ? 'Expand sidebar' : 'Minimize sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Minimize sidebar'}
        >
          <svg
            viewBox="0 0 24 24"
            className={`w-4 h-4 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>

        {/* Brand */}
        <div
          className={`flex items-center justify-between h-20 px-6 ${
            collapsed ? 'lg:justify-center lg:px-0' : ''
          }`}
        >
          <div className="flex items-center gap-3">
            <img
              src={mainLogo}
              alt=""
              className="w-10 h-10 p-1 rounded-xl bg-white object-contain shadow-[0_0_0_3px_rgba(246,178,60,0.25),0_4px_0_#cfcfcf]"
            />
            <div className={hideWhenMin}>
              <p className="text-lg font-extrabold tracking-wide dash-gradient-text whitespace-nowrap">
                AgroShift AI
              </p>
              <p className="text-[10px] font-mono tracking-[0.2em] text-sky-300/80 uppercase whitespace-nowrap">
                Mission control
              </p>
            </div>
          </div>
          <button
            className="lg:hidden p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10"
            onClick={onClose}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        {/* Nav */}
        <nav className={`flex-1 py-4 space-y-1 overflow-y-auto overflow-x-hidden ${collapsed ? 'px-4 lg:px-3' : 'px-4'}`}>
          <p className={`px-3 mb-2 text-[10px] font-semibold tracking-[0.18em] text-white/40 uppercase ${hideWhenMin}`}>
            Workspace
          </p>
          {NAV_ITEMS.map((item) => {
            const active = item.id === activeId;
            return (
              <button
                key={item.id}
                type="button"
                disabled={item.soon}
                onClick={() => {
                  onNavigate?.(item.id);
                  onClose?.();
                }}
                title={collapsed ? item.label : undefined}
                aria-label={item.label}
                aria-current={active ? 'page' : undefined}
                className={`group relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition
                  ${collapsed ? 'lg:justify-center lg:px-0' : ''}
                  ${active
                    ? 'bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]'
                    : 'text-white/65 hover:bg-white/5 hover:text-white'}
                  disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {active && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b from-amber-300 to-green-400 shadow-[0_0_12px_rgba(95,191,74,0.8)]" />
                )}
                <span className={active ? 'text-green-300' : 'text-white/50 group-hover:text-white/80'}>
                  {item.icon}
                </span>
                <span className={`whitespace-nowrap ${hideWhenMin}`}>{item.label}</span>
                {item.soon && (
                  <span className={`ml-auto px-2 py-0.5 text-[10px] font-semibold rounded-full bg-sky-400/15 text-sky-300 ${hideWhenMin}`}>
                    Soon
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User */}
        <div
          className={`flex items-center gap-3 px-5 py-4 border-t border-white/10 ${
            collapsed ? 'lg:flex-col lg:px-0' : ''
          }`}
        >
          <div
            className="w-9 h-9 shrink-0 rounded-full bg-gradient-to-br from-amber-300 to-green-500 text-slate-900 flex items-center justify-center font-bold text-sm uppercase"
            title={email}
          >
            {email[0]}
          </div>
          <p className={`flex-1 min-w-0 text-sm text-white/80 truncate ${hideWhenMin}`} title={email}>
            {email}
          </p>
          <button
            type="button"
            onClick={handleLogout}
            className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-red-500/80 transition"
            aria-label="Sign out"
            title="Sign out"
          >
            {icon(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /></>)}
          </button>
        </div>
      </aside>
    </>
  );
}
