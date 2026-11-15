import { useEffect, useRef, useState } from 'react';
import { sendChatMessage } from '../services/api';
import { CHAT_LANGUAGES, detectLanguage } from '../utils/language';
import { useVoice } from '../hooks/useVoice';

/*
  Farm assistant chat (POST /api/chat/) with voice.
  - Replies in the language you write in (Auto), or the one you pick.
  - 🎤 speak your question; 🔊 hear the answer (browser Web Speech API).
  Props:
    analysis – latest analysis (or null) so answers can use it
*/

const SUGGESTIONS = [
  'Tell me about wheat',
  'گندم کے بارے میں بتائیں',
  'چاول کو کتنا پانی چاہیے؟',
  'Which strategy is best for my farm?',
];

const WELCOME = {
  from: 'bot',
  lang: 'en',
  welcome: true,
  text: "Hi! Ask me about a crop or your farm's analysis — in English, اردو, سنڌي or پنجابی. You can also tap 🎤 and speak.",
};

export default function ChatPanel({ analysis }) {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [langMode, setLangMode] = useState('auto'); // 'auto' or a fixed language code
  const [lastLang, setLastLang] = useState('ur'); // language the mic uses in Auto mode
  const [voiceReplies, setVoiceReplies] = useState(false);
  const [notice, setNotice] = useState('');
  const listRef = useRef(null);
  const voice = useVoice();

  const micLang = langMode === 'auto' ? lastLang : langMode;

  // Keep the newest message in view
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const speakReply = (text, lang, id) => {
    const ok = voice.speak(text, CHAT_LANGUAGES[lang].speech, id);
    if (!ok) {
      setNotice(
        `No ${CHAT_LANGUAGES[lang].label} voice is installed on this device. ` +
          'Try Microsoft Edge, or add the language under Windows Settings → Time & language → Speech.'
      );
    }
  };

  const send = async (text) => {
    const message = text.trim();
    if (!message || sending) return;

    const lang = langMode === 'auto' ? detectLanguage(message) : langMode;
    setLastLang(lang);
    setNotice('');

    // Conversation so far (without the welcome text and error bubbles) + the new question
    const history = [
      ...messages
        .filter((m) => !m.welcome && !m.error)
        .map((m) => ({ role: m.from === 'me' ? 'user' : 'assistant', content: m.text })),
      { role: 'user', content: message },
    ];

    setMessages((m) => [...m, { from: 'me', text: message, lang }]);
    setInput('');
    setSending(true);

    try {
      const { reply } = await sendChatMessage(history, analysis, lang);
      setMessages((m) => [...m, { from: 'bot', text: reply, lang }]);
      // The reply's position: current messages + the question just added
      if (voiceReplies) speakReply(reply, lang, messages.length + 1);
    } catch (err) {
      setMessages((m) => [...m, { from: 'bot', text: `⚠️ ${err.message}`, error: true, lang: 'en' }]);
    } finally {
      setSending(false);
    }
  };

  const toggleMic = () => {
    if (voice.listening) {
      voice.stopListening();
      return;
    }
    setNotice('');
    voice.stopSpeaking();
    voice.listen(CHAT_LANGUAGES[micLang].speech, {
      onInterim: setInput,
      onFinal: (text) => send(text), // send as soon as you stop talking
      onError: setNotice,
    });
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      {/* Toolbar: language + voice replies */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-slate-100">
        <div className="flex flex-wrap p-1 bg-slate-100 rounded-xl" role="group" aria-label="Reply language">
          {[['auto', 'Auto'], ...Object.entries(CHAT_LANGUAGES).map(([k, v]) => [k, v.label])].map(
            ([code, label]) => (
              <button
                key={code}
                type="button"
                onClick={() => setLangMode(code)}
                aria-pressed={langMode === code}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${
                  langMode === code ? 'bg-white text-green-800 shadow' : 'text-slate-600 hover:text-slate-900'
                }`}
                title={code === 'auto' ? 'Reply in the language you write in' : undefined}
              >
                {label}
              </button>
            )
          )}
        </div>

        {voice.canSpeak && (
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={voiceReplies}
              onChange={(e) => {
                setVoiceReplies(e.target.checked);
                if (!e.target.checked) voice.stopSpeaking();
              }}
              className="w-4 h-4 accent-green-600"
            />
            🔊 Read replies aloud
          </label>
        )}
      </div>

      {/* Messages */}
      <div ref={listRef} className="h-80 overflow-y-auto p-5 space-y-3 bg-slate-50/60">
        {messages.map((m, i) => {
          const rtl = CHAT_LANGUAGES[m.lang]?.rtl;
          return (
            <div key={i} className={`flex items-end gap-1.5 ${m.from === 'me' ? 'justify-end' : 'justify-start'}`}>
              <div
                dir="auto"
                className={`max-w-[80%] px-4 py-2.5 rounded-2xl ${rtl ? 'text-base leading-loose' : 'text-sm leading-relaxed'} ${
                  m.from === 'me'
                    ? 'bg-green-600 text-white rounded-br-md'
                    : m.error
                      ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-md'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md'
                }`}
              >
                {m.text}
              </div>

              {/* Listen to this reply */}
              {m.from === 'bot' && !m.error && voice.canSpeak && (
                <button
                  type="button"
                  onClick={() =>
                    voice.speakingId === i ? voice.stopSpeaking() : speakReply(m.text, m.lang, i)
                  }
                  className={`shrink-0 p-1.5 rounded-lg text-sm transition ${
                    voice.speakingId === i ? 'bg-green-100 text-green-700' : 'text-slate-400 hover:text-green-700 hover:bg-green-50'
                  }`}
                  aria-label={voice.speakingId === i ? 'Stop reading' : 'Read aloud'}
                  title={voice.speakingId === i ? 'Stop' : 'Read aloud'}
                >
                  {voice.speakingId === i ? '⏹' : '🔊'}
                </button>
              )}
            </div>
          );
        })}
        {sending && (
          <div className="flex justify-start">
            <div className="px-4 py-2.5 rounded-2xl rounded-bl-md bg-white border border-slate-200 text-sm text-slate-400">
              Typing…
            </div>
          </div>
        )}
      </div>

      {/* Voice / permission notices */}
      {notice && (
        <p className="mx-5 mt-3 px-3 py-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg" role="status">
          {notice}
        </p>
      )}

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 px-5 pt-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            dir="auto"
            onClick={() => send(s)}
            disabled={sending}
            className="px-3 py-1.5 text-xs font-medium text-green-800 bg-green-50 border border-green-200 rounded-full hover:bg-green-100 disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 p-4"
      >
        {voice.canListen && (
          <button
            type="button"
            onClick={toggleMic}
            disabled={sending}
            className={`relative shrink-0 w-11 h-11 flex items-center justify-center rounded-xl border transition ${
              voice.listening
                ? 'bg-red-500 border-red-500 text-white'
                : 'bg-white border-slate-300 text-slate-600 hover:text-green-700 hover:border-green-500'
            } disabled:opacity-50`}
            aria-label={voice.listening ? 'Stop listening' : `Speak (${CHAT_LANGUAGES[micLang].label})`}
            title={voice.listening ? 'Stop listening' : `Speak — listening in ${CHAT_LANGUAGES[micLang].label}`}
          >
            {voice.listening && <span className="absolute inset-0 rounded-xl bg-red-400 animate-ping opacity-40" />}
            <svg viewBox="0 0 24 24" className="relative w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
          </button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          dir="auto"
          placeholder={voice.listening ? 'Listening… speak now' : 'Ask a question… / سوال لکھیں…'}
          aria-label="Chat message"
          className="flex-1 min-w-0 px-4 py-2.5 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="px-5 py-2.5 text-sm font-semibold text-white bg-green-600 rounded-xl hover:bg-green-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
