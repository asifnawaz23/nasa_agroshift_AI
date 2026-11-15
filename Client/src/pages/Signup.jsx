import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import AuthShell, { IconInput, PasswordInput } from '../components/AuthShell.jsx';
import * as yup from 'yup';
import { useForm, useWatch } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { loginSuccess } from '../features/auth/authSlice.js';
import { signup } from '../services/auth';

const signupSchema = yup.object().shape({
  fullName: yup.string().trim().required('Full name is required'),
  email: yup.string().email('Invalid email address').required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], 'Passwords do not match')
    .required('Please confirm your password'),
});

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
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(signupSchema),
    defaultValues: { fullName: '', email: '', password: '', confirmPassword: '' },
  });

  const password = useWatch({ control, name: 'password' });
  const score = passwordScore(password);

  const onSubmit = async (values) => {
    setServerError('');
    try {
      // POST /api/auth/signup/ -> { user, token }  (logs the user straight in)
      const { user, token } = await signup(values);
      dispatch(loginSuccess({ user, token }));
      navigate('/');
    } catch (err) {
      setServerError(err.message);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Satellite insights for your farm, free to start."
    >
      {serverError && (
        <div className="login3d__error mb-5" role="alert">
          {serverError}
        </div>
      )}

      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div>
          <label htmlFor="fullName" className="login3d__label">
            Full name
          </label>
          <IconInput
            icon="user"
            id="fullName"
            type="text"
            autoComplete="name"
            placeholder="Alex Morgan"
            aria-invalid={!!errors.fullName}
            {...register('fullName')}
          />
          {errors.fullName && <p className="login3d__hint">{errors.fullName.message}</p>}
        </div>

        <div>
          <label htmlFor="email" className="login3d__label">
            Email address
          </label>
          <IconInput
            icon="mail"
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={!!errors.email}
            {...register('email')}
          />
          {errors.email && <p className="login3d__hint">{errors.email.message}</p>}
        </div>

        <div>
          <label htmlFor="password" className="login3d__label">
            Password
          </label>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            placeholder="Min. 8 characters"
            aria-invalid={!!errors.password}
            {...register('password')}
          />
          {password && (
            <div className="login3d__strength" data-score={score}>
              <div className="login3d__strength-bars" aria-hidden="true">
                {[1, 2, 3, 4].map((n) => (
                  <span key={n} className={n <= score ? 'is-on' : ''} />
                ))}
              </div>
              <span className="login3d__strength-label">{STRENGTH_LABELS[score]}</span>
            </div>
          )}
          {errors.password && <p className="login3d__hint">{errors.password.message}</p>}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="login3d__label">
            Confirm password
          </label>
          <PasswordInput
            icon="shield"
            id="confirmPassword"
            autoComplete="new-password"
            placeholder="••••••••"
            aria-invalid={!!errors.confirmPassword}
            {...register('confirmPassword')}
          />
          {errors.confirmPassword && (
            <p className="login3d__hint">{errors.confirmPassword.message}</p>
          )}
        </div>

        <button type="submit" className="login3d__btn" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
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
