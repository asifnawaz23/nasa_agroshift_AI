import { useState } from 'react';

/*
  Round user avatar: the profile picture if there is one, otherwise the first letter.
  Props:
    user      – { full_name, email, profile_picture }
    size      – Tailwind size classes, e.g. "w-9 h-9 text-sm"
    className – extra classes (rings, shadows…)
*/
export default function Avatar({ user, size = 'w-9 h-9 text-sm', className = '' }) {
  // If the image URL is broken, fall back to the letter
  const [failedUrl, setFailedUrl] = useState(null);
  const url = user?.profile_picture;
  const letter = (user?.full_name || user?.email || '?')[0];

  if (url && url !== failedUrl) {
    return (
      <img
        src={url}
        alt=""
        onError={() => setFailedUrl(url)}
        className={`${size} shrink-0 rounded-full object-cover bg-slate-200 ${className}`}
      />
    );
  }

  return (
    <div
      className={`${size} shrink-0 rounded-full bg-gradient-to-br from-amber-300 to-green-500 text-slate-900 flex items-center justify-center font-bold uppercase ${className}`}
    >
      {letter}
    </div>
  );
}
