import { useRef, useState } from 'react';
import mainLogo from '../assets/mainLogo.jpg';
import '../pages/Login3D.css';

// Shared space + farmland scene and 3D tilt card used by Login and Signup.

const MAX_TILT = 10; // degrees

// Pseudo-random but deterministic, so render stays pure
const rand = (i, n, seed) => (Math.sin(i * seed + n * 13.7) + 1) / 2;

const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  id: i,
  left: `${rand(i, 1, 97.13) * 100}%`,
  delay: `${-rand(i, 2, 97.13) * 14}s`,
  duration: `${10 + rand(i, 3, 97.13) * 10}s`,
  size: `${3 + rand(i, 4, 97.13) * 5}px`,
}));

// Starfield, kept in the upper (space) part of the screen
const STARS = Array.from({ length: 70 }, (_, i) => ({
  id: i,
  left: `${rand(i, 1, 53.71) * 100}%`,
  top: `${rand(i, 2, 53.71) * 55}%`,
  size: `${1 + rand(i, 3, 53.71) * 2}px`,
  delay: `${-rand(i, 4, 53.71) * 4}s`,
  duration: `${2 + rand(i, 5, 53.71) * 4}s`,
}));

export default function AuthShell({ title, subtitle, children }) {
  const cardRef = useRef(null);

  // 3D tilt that follows the mouse (pointer devices only)
  const handleMouseMove = (e) => {
    const card = cardRef.current;
    if (!card || window.matchMedia('(hover: none)').matches) return;
    const r = card.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width; // 0..1
    const py = (e.clientY - r.top) / r.height; // 0..1
    card.style.setProperty('--ry', `${(px - 0.5) * 2 * MAX_TILT}deg`);
    card.style.setProperty('--rx', `${(0.5 - py) * 2 * MAX_TILT}deg`);
    card.style.setProperty('--gx', `${px * 100}%`);
    card.style.setProperty('--gy', `${py * 100}%`);
  };

  const resetTilt = () => {
    const card = cardRef.current;
    if (!card) return;
    card.style.setProperty('--rx', '0deg');
    card.style.setProperty('--ry', '0deg');
    card.style.setProperty('--gx', '50%');
    card.style.setProperty('--gy', '0%');
  };

  return (
    <div className="login3d">
      {/* Background scene */}
      <div className="login3d__stars" aria-hidden="true">
        {STARS.map((s) => (
          <span
            key={s.id}
            style={{
              left: s.left,
              top: s.top,
              width: s.size,
              height: s.size,
              animationDelay: s.delay,
              animationDuration: s.duration,
            }}
          />
        ))}
      </div>
      <div className="login3d__earth-wrap" aria-hidden="true">
        <div className="login3d__earth" />
        <div className="login3d__orbit">
          <div className="login3d__sat" />
        </div>
      </div>
      <div className="login3d__moon" aria-hidden="true" />
      <div className="login3d__floor" aria-hidden="true">
        <div className="login3d__floor-plane" />
        <div className="login3d__scan" />
      </div>
      <div className="login3d__particles" aria-hidden="true">
        {PARTICLES.map((p) => (
          <span
            key={p.id}
            style={{
              left: p.left,
              width: p.size,
              height: p.size,
              animationDelay: p.delay,
              animationDuration: p.duration,
            }}
          />
        ))}
      </div>

      {/* Card */}
      <div
        className="login3d__stage"
        onMouseMove={handleMouseMove}
        onMouseLeave={resetTilt}
      >
        <div className="login3d__card" ref={cardRef}>
          <div className="login3d__glare" aria-hidden="true" />

          <header className="text-center login3d__z3">
            <div className="login3d__logo">
              <img src={mainLogo} alt="AgroShift AI logo" />
            </div>
            <h1 className="login3d__brand">AgroShift AI</h1>
          </header>

          <div className="text-center login3d__z2">
            <h2 className="login3d__title mt-3">{title}</h2>
            {subtitle && <p className="login3d__subtitle">{subtitle}</p>}
          </div>

          <div className="mt-7 login3d__z1">{children}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Shared form pieces ---------- */

const svgProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
};

const ICONS = {
  mail: (
    <svg className="login3d__icon" {...svgProps}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  ),
  lock: (
    <svg className="login3d__icon" {...svgProps}>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  ),
  user: (
    <svg className="login3d__icon" {...svgProps}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </svg>
  ),
  shield: (
    <svg className="login3d__icon" {...svgProps}>
      <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  ),
};

/** Text input with a leading icon. Pass `icon` = mail | lock | user | shield. */
export function IconInput({ icon, ...inputProps }) {
  return (
    <div className="login3d__field">
      {ICONS[icon]}
      <input className="login3d__input" {...inputProps} />
    </div>
  );
}

/** Password input with leading icon and show/hide toggle. */
export function PasswordInput({ icon = 'lock', ...inputProps }) {
  const [show, setShow] = useState(false);
  return (
    <div className="login3d__field">
      {ICONS[icon]}
      <input
        className="login3d__input"
        type={show ? 'text' : 'password'}
        {...inputProps}
      />
      <button
        type="button"
        className="login3d__toggle"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? 'Hide password' : 'Show password'}
      >
        {show ? (
          <svg {...svgProps}>
            <path d="M3 3l18 18" />
            <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
            <path d="M9.9 5.1A9.8 9.8 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.1 6.1A17 17 0 0 0 2 12s4 7 10 7a9.6 9.6 0 0 0 4.2-.9" />
          </svg>
        ) : (
          <svg {...svgProps}>
            <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}
