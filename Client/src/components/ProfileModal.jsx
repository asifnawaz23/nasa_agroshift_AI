import { createPortal } from 'react-dom';
import { useSelector } from 'react-redux';

/*
  Shows the logged-in user's info from Redux (state.auth).
  Props:
    open    – show the modal?
    onClose – close it
*/
export default function ProfileModal({ open, onClose }) {
  const { user, isAuthenticated } = useSelector((state) => state.auth);

  if (!open) return null;

  const email = user?.email ?? 'Unknown';
  const name = user?.name ?? email.split('@')[0];

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
        {/* Header */}
        <div className="flex flex-col items-center px-6 pt-8 pb-6 bg-gradient-to-br from-slate-900 to-emerald-900 text-white">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-300 to-green-500 text-slate-900 flex items-center justify-center text-2xl font-bold uppercase">
            {name[0]}
          </div>
          <h2 id="profile-title" className="mt-3 text-lg font-semibold capitalize">
            {name}
          </h2>
          <p className="text-sm text-white/70">{email}</p>
        </div>

        {/* Details */}
        <dl className="px-6 py-4 divide-y divide-gray-100 text-sm">
          <div className="flex justify-between py-2.5">
            <dt className="text-gray-500">Email</dt>
            <dd className="font-medium text-gray-900">{email}</dd>
          </div>
          <div className="flex justify-between py-2.5">
            <dt className="text-gray-500">Status</dt>
            <dd className={isAuthenticated ? 'font-medium text-green-700' : 'font-medium text-gray-500'}>
              {isAuthenticated ? 'Logged in' : 'Logged out'}
            </dd>
          </div>
        </dl>

        <div className="px-6 pb-6">
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
