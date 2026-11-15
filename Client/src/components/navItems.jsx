// Sidebar navigation items (kept separate so Sidebar.jsx only exports a component)

export const icon = (d) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5" aria-hidden="true">
    {d}
  </svg>
);

export const NAV_ITEMS = [
  {
    id: 'overview',
    label: 'Overview',
    icon: icon(<><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>),
  },
  {
    id: 'location',
    label: 'Farm Location',
    icon: icon(<><path d="M12 21s-7-6.1-7-11a7 7 0 0 1 14 0c0 4.9-7 11-7 11Z" /><circle cx="12" cy="10" r="2.5" /></>),
  },
  {
    id: 'details',
    label: 'Farm Details',
    icon: icon(<><path d="M12 22V12" /><path d="M12 12C12 7 8 4 3 4c0 5 4 8 9 8Z" /><path d="M12 15c0-4 3-6.5 8-6.5 0 4-3 6.5-8 6.5Z" /></>),
  },
  {
    id: 'analysis',
    label: 'Analysis',
    icon: icon(<><path d="M3 3v18h18" /><rect x="7" y="12" width="3" height="6" rx="1" /><rect x="12" y="8" width="3" height="10" rx="1" /><rect x="17" y="5" width="3" height="13" rx="1" /></>),
  },
  {
    id: 'whatif',
    label: 'What-If',
    icon: icon(<><path d="M14 4v10.5a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" /><path d="M12 14v3" /></>),
  },
  {
    id: 'assistant',
    label: 'AI Assistant',
    icon: icon(<><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" /><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" /></>),
  },
];
