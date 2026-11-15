import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { IconInput, PasswordInput } from '../components/AuthShell.jsx';
import * as yup from 'yup';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { useDispatch } from 'react-redux';
import { loginSuccess } from '../features/auth/authSlice.js';
import { login } from '../services/auth';


const loginSchema = yup.object().shape({
  email: yup.string().email('Invalid email address').required('Email is required'),
  password: yup.string().required('Password is required'),
});

export default function Login() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  // Only runs when the yup schema passes
  const onSubmit = async ({ email, password }) => {
    setServerError('');
    try {
      // POST /api/auth/login/ -> { user, token }
      const { user, token } = await login({ email, password });
      dispatch(loginSuccess({ user, token }));
      navigate('/');
    } catch (err) {
      setServerError(err.message);
    }
  };

  return (
    <AuthShell
      title="Sign in to your account"
      subtitle="Welcome back to your farm dashboard."
    >
      {serverError && (
        <div className="login3d__error mb-5" role="alert">
          {serverError}
        </div>
      )}

      <form
        className="space-y-5"
        onSubmit={handleSubmit(onSubmit)}
        noValidate
      >
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
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
          {errors.email && (
            <p id="email-error" className="login3d__hint" role="alert">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="login3d__label">
            Password
          </label>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
          {errors.password && (
            <p id="password-error" className="login3d__hint" role="alert">
              {errors.password.message}
            </p>
          )}
        </div>

        <button type="submit" className="login3d__btn" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="login3d__footer login3d__z1">
        Don&apos;t have an account?{' '}
        <Link to="/signup" className="login3d__link" style={{ fontSize: '0.85rem' }}>
          Sign up
        </Link>
      </p>
    </AuthShell>
  );
}
