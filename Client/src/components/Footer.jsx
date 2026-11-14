import mainLogo from '../assets/mainLogo.jpg';

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-12 border-t border-slate-200 bg-white/60 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Brand + mission */}
        <div className="flex items-center gap-3">
          <img
            src={mainLogo}
            alt=""
            className="w-9 h-9 p-1 rounded-lg bg-white object-contain ring-1 ring-slate-200"
          />
          <div>
            <p className="text-sm font-semibold text-slate-900">
              AgroShift AI{' '}
              <span className="font-normal text-slate-500">
                — Helping farmers, not replacing agricultural experts.
              </span>
            </p>
            <p className="text-xs text-slate-400">
              Built with NASA Earth observation data 🌍🌱
            </p>
          </div>
        </div>

        {/* Copyright */}
        <p className="text-xs text-slate-400">© {year} AgroShift AI</p>
      </div>

      {/* Disclaimer */}
      <div className="border-t border-slate-100">
        <p className="max-w-7xl mx-auto px-4 sm:px-8 py-3 text-[11px] leading-relaxed text-slate-400">
          Recommendations are for decision support only and do not guarantee yields or income.
          Always check with a local agricultural expert before making major changes to your farm.
        </p>
      </div>
    </footer>
  );
}
