import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch, useSelector } from 'react-redux';
import { getMe, removeProfilePicture, uploadProfilePicture } from '../services/api';
import { updateUser } from '../features/auth/authSlice';
import Avatar from './Avatar';

/*
  Shows the logged-in user's info and lets them change their profile picture.
  - Refreshes the user from GET /api/auth/me/ when opened
  - Uploads to POST /api/auth/profile-picture/ (stored on Cloudinary)
  - Removes with DELETE /api/auth/profile-picture/
  Props:
    open    – show the modal?
    onClose – close it
*/

const MAX_MB = 5;
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export default function ProfileModal({ open, onClose }) {
  const dispatch = useDispatch();
  const { user, isAuthenticated } = useSelector((state) => state.auth);
  const fileRef = useRef(null);

  const [preview, setPreview] = useState(null); // local image shown while uploading
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Refresh the stored user (and so every avatar) when the modal opens
  useEffect(() => {
    if (!open) return;
    getMe()
      .then((data) => dispatch(updateUser(data.user)))
      .catch(() => {}); // keep showing the stored user
  }, [open, dispatch]);

  // Free the preview image's memory when it changes or the modal unmounts
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  if (!open) return null;

  const email = user?.email ?? 'Unknown';
  const name = user?.full_name || user?.name || email.split('@')[0];
  const joined = user?.date_joined ? new Date(user.date_joined).toLocaleDateString() : null;

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow picking the same file again later
    if (!file) return;

    setError('');
    setMessage('');
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Please choose a JPG, PNG or WebP image.');
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`Image must be ${MAX_MB} MB or smaller.`);
      return;
    }

    setPreview(URL.createObjectURL(file));
    setBusy(true);
    try {
      const data = await uploadProfilePicture(file);
      dispatch(updateUser(data.user));
      setMessage('Profile picture updated.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setPreview(null);
    }
  };

  const handleRemove = async () => {
    setError('');
    setMessage('');
    setBusy(true);
    try {
      const data = await removeProfilePicture();
      dispatch(updateUser(data.user));
      setMessage('Profile picture removed.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  // Portal: render on <body> so no parent styles can trap the overlay
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-title"
        className="w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with photo */}
        <div className="flex flex-col items-center px-6 pt-8 pb-6 bg-gradient-to-br from-slate-900 to-emerald-900 text-white">
          <div className="relative">
            <Avatar
              user={preview ? { ...user, profile_picture: preview } : user}
              size="w-24 h-24 text-3xl"
              className={`ring-4 ring-white/20 ${busy ? 'opacity-60' : ''}`}
            />
            {busy && (
              <span className="absolute inset-0 flex items-center justify-center">
                <span className="w-8 h-8 rounded-full border-[3px] border-white border-t-transparent animate-spin" />
              </span>
            )}
            {/* Small camera button on the photo */}
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="absolute -bottom-1 -right-1 flex items-center justify-center w-9 h-9 rounded-full bg-green-500 text-white shadow-lg ring-4 ring-slate-900 hover:bg-green-600 disabled:opacity-50"
              aria-label="Change profile picture"
              title="Change profile picture"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 8h3l2-3h6l2 3h3v11H4Z" />
                <circle cx="12" cy="13" r="3.5" />
              </svg>
            </button>
          </div>

          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFile}
            className="hidden"
          />

          <h2 id="profile-title" className="mt-4 text-lg font-semibold capitalize">
            {name}
          </h2>
          <p className="text-sm text-white/70">{email}</p>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-50"
            >
              {busy ? 'Uploading…' : user?.profile_picture ? 'Change photo' : 'Upload photo'}
            </button>
            {user?.profile_picture && (
              <button
                type="button"
                onClick={handleRemove}
                disabled={busy}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/10 hover:bg-red-500/80 disabled:opacity-50"
              >
                Remove
              </button>
            )}
          </div>
        </div>

        {/* Upload feedback */}
        {(error || message) && (
          <p
            role={error ? 'alert' : 'status'}
            className={`mx-6 mt-4 px-3 py-2 text-sm rounded-lg ${
              error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
            }`}
          >
            {error || message}
          </p>
        )}

        {/* Details */}
        <dl className="px-6 py-4 divide-y divide-gray-100 text-sm">
          <div className="flex justify-between gap-4 py-2.5">
            <dt className="text-gray-500">Email</dt>
            <dd className="font-medium text-gray-900 truncate">{email}</dd>
          </div>
          {joined && (
            <div className="flex justify-between py-2.5">
              <dt className="text-gray-500">Member since</dt>
              <dd className="font-medium text-gray-900">{joined}</dd>
            </div>
          )}
          <div className="flex justify-between py-2.5">
            <dt className="text-gray-500">Status</dt>
            <dd className={isAuthenticated ? 'font-medium text-green-700' : 'font-medium text-gray-500'}>
              {isAuthenticated ? 'Logged in' : 'Logged out'}
            </dd>
          </div>
        </dl>

        <div className="px-6 pb-6">
          <p className="mb-3 text-xs text-gray-400 text-center">JPG, PNG or WebP · max {MAX_MB} MB</p>
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
