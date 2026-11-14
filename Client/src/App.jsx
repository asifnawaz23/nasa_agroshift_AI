
import { Routes, Route } from 'react-router-dom';

import Landing from './pages/Landing.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';
import Signup from './pages/Signup.jsx';
import { useSelector } from 'react-redux';
import './App.css';

function App() {

  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated)

  return (
    <Routes>
      
          {/* Conditional Root Route: 
          If logged in, show Dashboard. Otherwise, show LandingPage.  */}
        
      <Route
        path="/"
        element={isAuthenticated ? <Dashboard /> : <Landing />}
      />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
    </Routes>
  );
}

export default App;
