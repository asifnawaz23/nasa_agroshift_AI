import { useState } from 'react';
import { explainAnalysis } from '../services/api';

/*
  "Why this recommendation" box with a language switch.
  Calls POST /api/explain/ again whenever the farmer picks another language.
  Props:
    analysis     – the /api/analyze/ response
    initial      – explanation already fetched in English (optional)
*/

const LANGUAGES = [
  { code: 'en', label: 'English', rtl: false },
  { code: 'ur', label: 'اردو', rtl: true },
  { code: 'sd', label: 'سنڌي', rtl: true },
  { code: 'pa', label: 'پنجابی', rtl: true },
];

const POINT_LABELS = {
  observed: 'Observed',
  estimated_cause: 'Likely cause',
  prediction: 'Prediction',
};

export default function ExplanationCard({ analysis, initial }) {
  const [lang, setLang] = useState('en');
  // Keep every language we've already fetched so switching back is instant
  const [byLang, setByLang] = useState(initial ? { en: initial } : {});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const data = byLang[lang];
  const rtl = LANGUAGES.find((l) => l.code === lang)?.rtl;
  const text = data?.summary || data?.explanation;

  const switchLanguage = async (code) => {
    setLang(code);
    setError('');
    if (byLang[code]) return;
    setLoading(true);
    try {
      const result = await explainAnalysis(analysis, code);
      setByLang((prev) => ({ ...prev, [code]: result }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-50 to-white border border-emerald-200">
      {/* Header + language switch */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl" aria-hidden="true">💡</span>
          <p className="text-sm font-semibold text-emerald-900">Why this recommendation</p>
          {data && (
            <span
              className={`px-2 py-0.5 text-[11px] font-semibold rounded-full ${
                data.ai_used ? 'bg-violet-100 text-violet-800' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {data.ai_used ? '✨ AI explanation' : 'Basic summary'}
            </span>
          )}
        </div>

        <div className="flex p-1 bg-white rounded-xl border border-emerald-200 shadow-sm" role="group" aria-label="Explanation language">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => switchLanguage(l.code)}
              aria-pressed={lang === l.code}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${
                lang === l.code ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:text-emerald-800'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div dir={rtl ? 'rtl' : 'ltr'} lang={lang} className={`mt-3 text-start ${rtl ? 'leading-loose' : ''}`}>
        {loading && <p className="text-sm text-slate-500">Translating…</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}

        {!loading && text && (
          <p className={`text-slate-700 ${rtl ? 'text-base' : 'text-sm leading-relaxed'}`}>{text}</p>
        )}

        {!loading && data?.points?.length > 0 && (
          <ul dir="auto" className="mt-3 space-y-1.5">
            {data.points.map((p, i) => (
              // dir="auto": an English line inside the Urdu/Sindhi view still reads left-to-right
              <li key={i} dir="auto" className="text-sm text-slate-700">
                <span className="inline-block px-1.5 py-0.5 me-1.5 text-[10px] font-semibold rounded bg-sky-100 text-sky-800" dir="ltr">
                  {POINT_LABELS[p.type] || p.type}
                </span>
                {p.text}
                {p.source && <span className="text-xs text-slate-400" dir="ltr"> ({p.source})</span>}
              </li>
            ))}
          </ul>
        )}

        {!loading && data?.actions?.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide" dir="ltr">
              What you can do
            </p>
            <ul dir="auto" className="mt-1 list-disc ps-5 space-y-1 text-sm text-slate-700">
              {data.actions.map((a, i) => <li key={i} dir="auto">{a}</li>)}
            </ul>
          </div>
        )}

        {!loading && data?.needs_expert?.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide" dir="ltr">
              Check with a local expert
            </p>
            <ul dir="auto" className="mt-1 list-disc ps-5 space-y-1 text-sm text-slate-700">
              {data.needs_expert.map((a, i) => <li key={i} dir="auto">{a}</li>)}
            </ul>
          </div>
        )}
      </div>

      {data && !data.ai_used && lang !== 'en' && (
        <p className="mt-3 text-xs text-slate-500">
          Only the summary is translated in basic mode. Full translation needs the AI explanation
          (an LLM_API_KEY on the backend).
        </p>
      )}
    </div>
  );
}
