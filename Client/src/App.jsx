
import { Routes, Route, Navigate } from 'react-router-dom';

import Dashboard from './pages/Dashboard.jsx';
import About from "./pages/About.jsx";
import './App.css';

function App() {
  // No accounts: everyone goes straight to the dashboard.
  // Old /login and /signup links (bookmarks, shared links) land on the dashboard too.
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/about" element={<About />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
