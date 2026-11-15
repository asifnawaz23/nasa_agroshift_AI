import { useCallback, useEffect, useRef, useState } from 'react';

/*
  Voice helpers using the browser's built-in Web Speech API (no API key, no package).
  - listen(lang, onText): speech -> text (best in Chrome and Edge)
  - speak(text, lang):    text -> speech (needs a voice for that language installed)
*/

const Recognition =
  typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

export function useVoice() {
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [voices, setVoices] = useState([]);
  const recognitionRef = useRef(null);

  const canListen = Boolean(Recognition);
  const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Voices load asynchronously in most browsers
  useEffect(() => {
    if (!canSpeak) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', load);
      window.speechSynthesis.cancel();
    };
  }, [canSpeak]);

  /** Find an installed voice for a language like "ur-PK" (prefers an exact match). */
  const voiceFor = useCallback(
    (speechLang) => {
      const base = speechLang.split('-')[0];
      return (
        voices.find((v) => v.lang === speechLang) ||
        voices.find((v) => v.lang.toLowerCase().startsWith(base)) ||
        null
      );
    },
    [voices]
  );

  /** Start listening. onInterim(text) while speaking, onFinal(text) when done. */
  const listen = useCallback(
    (speechLang, { onInterim, onFinal, onError }) => {
      if (!Recognition) return;
      recognitionRef.current?.abort();

      const rec = new Recognition();
      rec.lang = speechLang;
      rec.interimResults = true;
      rec.continuous = false;

      let finalText = '';
      rec.onresult = (e) => {
        let interim = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) finalText += t;
          else interim += t;
        }
        onInterim?.(finalText + interim);
      };
      rec.onerror = (e) => {
        if (e.error === 'no-speech' || e.error === 'aborted') return;
        onError?.(
          e.error === 'not-allowed'
            ? 'Microphone access is blocked. Allow it from the 🔒 icon in the address bar.'
            : e.error === 'language-not-supported'
              ? 'This browser cannot listen in that language.'
              : `Voice input error: ${e.error}`
        );
      };
      rec.onend = () => {
        setListening(false);
        if (finalText.trim()) onFinal?.(finalText.trim());
      };

      recognitionRef.current = rec;
      setListening(true);
      rec.start();
    },
    []
  );

  const stopListening = useCallback(() => recognitionRef.current?.stop(), []);

  /** Read text aloud. Returns false if no voice exists for that language. */
  const speak = useCallback(
    (text, speechLang, id = null) => {
      if (!canSpeak) return false;
      const voice = voiceFor(speechLang);
      if (!voice) return false;

      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.voice = voice;
      u.lang = voice.lang;
      u.rate = 0.95;
      u.onend = () => setSpeakingId(null);
      u.onerror = () => setSpeakingId(null);
      setSpeakingId(id);
      window.speechSynthesis.speak(u);
      return true;
    },
    [canSpeak, voiceFor]
  );

  const stopSpeaking = useCallback(() => {
    if (canSpeak) window.speechSynthesis.cancel();
    setSpeakingId(null);
  }, [canSpeak]);

  return {
    canListen,
    canSpeak,
    listening,
    speakingId,
    hasVoiceFor: (speechLang) => Boolean(voiceFor(speechLang)),
    listen,
    stopListening,
    speak,
    stopSpeaking,
  };
}
