import { useRef } from 'react';
import { Link } from 'react-router-dom';
import mainLogo from '../assets/mainLogo.jpg';
import './Landing.css';

// Pseudo-random but deterministic, so render stays pure
const rand = (i, n, seed) => {
  const x = Math.sin(i * seed + n * 78.233) * 43758.5453;
  return x - Math.floor(x); // 0..1, well scattered
};

const STARS = Array.from({ length: 90 }, (_, i) => ({
  id: i,
  left: `${rand(i, 1, 41.3) * 100}%`,
  top: `${rand(i, 2, 41.3) * 60}%`,
  size: `${1 + rand(i, 3, 41.3) * 2}px`,
  delay: `${-rand(i, 4, 41.3) * 4}s`,
  duration: `${2 + rand(i, 5, 41.3) * 4}s`,
}));

const SEEDS = Array.from({ length: 16 }, (_, i) => ({
  id: i,
  left: `${rand(i, 1, 77.7) * 100}%`,
  size: `${3 + rand(i, 2, 77.7) * 4}px`,
  delay: `${-rand(i, 3, 77.7) * 12}s`,
  duration: `${9 + rand(i, 4, 77.7) * 8}s`,
}));

export default function Landing() {
  const rootRef = useRef(null);

  // Gentle mouse parallax (pointer devices only)
  const handleMouseMove = (e) => {
    const el = rootRef.current;
    if (!el || window.matchMedia('(hover: none)').matches) return;
    const mx = (e.clientX / window.innerWidth - 0.5) * 2;
    const my = (e.clientY / window.innerHeight - 0.5) * 2;
    el.style.setProperty('--mx', mx.toFixed(3));
    el.style.setProperty('--my', my.toFixed(3));
  };

  return (
    <div className="land" ref={rootRef} onMouseMove={handleMouseMove}>
      {/* Background */}
      <div className="land__layer land__layer--far" aria-hidden="true">
        {STARS.map((s) => (
          <span
            key={s.id}
            className="land__star"
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
        <span className="land__shooting" />
      </div>
      <div className="land__floor" aria-hidden="true">
        <div className="land__floor-plane" />
        <div className="land__scan" />
      </div>
      <div className="land__layer land__layer--near" aria-hidden="true">
        {SEEDS.map((s) => (
          <span
            key={s.id}
            className="land__seed"
            style={{
              left: s.left,
              width: s.size,
              height: s.size,
              animationDelay: s.delay,
              animationDuration: s.duration,
            }}
          />
        ))}
      </div>

      {/* Nav */}
      <nav className="land__nav">
        <Link to="/" className="land__brand">
          <img src={mainLogo} alt="" />
          AgroShift AI
        </Link>
        <Link to="/login" className="land__nav-link">
          Sign in
        </Link>
      </nav>

      {/* Hero */}
      <main className="land__hero">
        <div className="land__copy">
          <span className="land__eyebrow">
            <span className="land__dot" aria-hidden="true" />
            Powered by satellite Earth data
          </span>
          <h1 className="land__title">
            Farm smarter
            <br />
            <em>from orbit.</em>
          </h1>
          <p className="land__sub">
            AI that turns what satellites see into clear decisions for every field you grow.
          </p>
          <Link to="/login" className="land__cta">
            Launch mission control
            <span className="land__cta-arrow" aria-hidden="true">→</span>
          </Link>
        </div>

        <div className="land__globe-stage" aria-hidden="true">
          <div className="land__glow" />
          <div className="land__ring land__ring--b">
            <div className="land__sat land__sat--gold" />
          </div>
          <div className="land__globe" />
          <div className="land__ring land__ring--a">
            <div className="land__sat" />
          </div>

          <div className="land__card land__card--a">
            <span className="land__card-icon">🌱</span>
            <div>
              <div className="land__card-label">Crop health</div>
              <div className="land__card-value">NDVI 0.82<small>▲ 6%</small></div>
            </div>
          </div>
          <div className="land__card land__card--b">
            <span className="land__card-icon">💧</span>
            <div>
              <div className="land__card-label">Soil moisture</div>
              <div className="land__card-value">34%<small>optimal</small></div>
            </div>
          </div>
          <div className="land__card land__card--c">
            <span className="land__card-icon">🌦️</span>
            <div>
              <div className="land__card-label">Rain forecast</div>
              <div className="land__card-value">In 2 days</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
