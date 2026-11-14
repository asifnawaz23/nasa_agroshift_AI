import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { IconInput, PasswordInput } from '../components/AuthShell.jsx';
import * as yup from 'yup'
import { useForm } from 'react-hook-form'
import { yupResolver } from '@hookform/resolvers/yup'

const signupSchema = yup.object().shape({
  fullName: yup.string().required(),
  email: yup.string().email().required(),
  password: yup.string().required(),
})

const STRENGTH_LABELS = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'];

// 0..4 score: length, mixed case, number, symbol
function passwordScore(pw) {
  if (!pw) return 0;
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}

export default function Signup() {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Add your registration API call here
    navigate('/login');
  };

  const score = passwordScore(formData.password);
  const confirmMismatch =
    formData.confirmPassword.length > 0 &&
    formData.password !== formData.confirmPassword;

  return (
    <AuthShell
      status="Ground station ready"
      title="Join the mission"
      subtitle="Create your account to get satellite insights for your farm."
    >
      {error && (
        <div className="login3d__error login3d__z1" role="alert">
          {error}
        </div>
      )}

      <form className="mt-7 space-y-5 login3d__z1" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="fullName" className="login3d__label">
            Full name
          </label>
          <IconInput
            icon="user"
            id="fullName"
            name="fullName"
            type="text"
            required
            autoComplete="name"
            value={formData.fullName}
            onChange={handleChange}
            placeholder="Alex Morgan"
          />
        </div>

        <div>
          <label htmlFor="email" className="login3d__label">
            Email address
          </label>
          <IconInput
            icon="mail"
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="login3d__label">
            Password
          </label>
          <PasswordInput
            id="password"
            name="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Min. 8 characters"
          />
          {formData.password && (
            <div className="login3d__strength" data-score={score}>
              <div className="login3d__strength-bars" aria-hidden="true">
                {[1, 2, 3, 4].map((n) => (
                  <span key={n} className={n <= score ? 'is-on' : ''} />
                ))}
              </div>
              <span className="login3d__strength-label">
                {STRENGTH_LABELS[score]}
              </span>
            </div>
          )}
        </div>

        <button type="submit" className="login3d__btn">
          🚀 Create account
        </button>
      </form>

      <p className="login3d__footer login3d__z1">
        Already have an account?{' '}
        <Link to="/login" className="login3d__link" style={{ fontSize: '0.85rem' }}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
