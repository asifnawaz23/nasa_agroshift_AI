// Chat languages: code sent to the backend, label, writing direction, speech codes.
export const CHAT_LANGUAGES = {
  en: { label: 'English', rtl: false, speech: 'en-US' },
  ur: { label: 'اردو', rtl: true, speech: 'ur-PK' },
  // Browsers have no Sindhi / Shahmukhi-Punjabi speech recognition, so the mic listens
  // in Urdu for these (the spoken words are close enough to type the question).
  sd: { label: 'سنڌي', rtl: true, speech: 'ur-PK' },
  pa: { label: 'پنجابی', rtl: true, speech: 'ur-PK' },
};

// Letters used in Sindhi but not in Urdu
const SINDHI_LETTERS = /[ڄڃڇڏڌڍڊٺٽٿڙڻڦڪڳڱٻ]/;
// Common Punjabi (Shahmukhi) words that Urdu doesn't use
const PUNJABI_WORDS = new Set([
  'دا', 'دی', 'دے', 'نوں', 'توں', 'وچ', 'نئیں', 'کیہ', 'تہاڈا', 'تہاڈی', 'تہاڈے',
  'ساڈا', 'ساڈی', 'ساڈے', 'اے', 'ہیگا', 'کنک', 'دسو', 'لوڑ',
]);

/** Guess the language of a message: en, ur, sd or pa. */
export function detectLanguage(text) {
  if (!/[؀-ۿ]/.test(text)) return 'en'; // no Arabic-script letters
  if (SINDHI_LETTERS.test(text)) return 'sd';
  const words = text.replace(/[؟?!.،,۔]/g, ' ').split(/\s+/);
  if (words.some((w) => PUNJABI_WORDS.has(w))) return 'pa';
  return 'ur';
}
