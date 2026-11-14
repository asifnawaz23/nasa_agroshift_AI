import { useEffect, useRef, useState } from 'react';
import { sendChatMessage } from '../services/api';

/*
  Simple chat box for POST /api/chat/
  Props:
    analysis – latest analysis (or null) so answers can use it
*/

const SUGGESTIONS = [
  'Tell me about wheat',
  'How much water does rice need?',
  'Which strategy is best for my farm?',
];

export default function ChatPanel({ analysis }) {
  const [messages, setMessages] = useState([
    {
      from: 'bot',
      text: "Hi! Ask me about a crop (e.g. wheat, rice, cotton) or about your farm's analysis.",
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  // Keep the newest message in view
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const send = async (text) => {
    const message = text.trim();
    if (!message || sending) return;

    setMessages((m) => [...m, { from: 'me', text: message }]);
    setInput('');
    setSending(true);

    try {
      const { reply } = await sendChatMessage(message, analysis);
      setMessages((m) => [...m, { from: 'bot', text: reply }]);
    } catch (err) {
      setMessages((m) => [...m, { from: 'bot', text: `⚠️ ${err.message}`, error: true }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      {/* Messages */}
      <div ref={listRef} className="h-80 overflow-y-auto p-5 space-y-3 bg-slate-50/60">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.from === 'me' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                m.from === 'me'
                  ? 'bg-green-600 text-white rounded-br-md'
                  : m.error
                    ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-md'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="px-4 py-2.5 rounded-2xl rounded-bl-md bg-white border border-slate-200 text-sm text-slate-400">
              Typing…
            </div>
          </div>
        )}
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 px-5 pt-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
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
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          aria-label="Chat message"
          className="flex-1 px-4 py-2.5 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500"
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
