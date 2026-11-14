import { Link, useNavigate } from 'react-router-dom';
import AuthShell, { IconInput, PasswordInput } from '../components/AuthShell.jsx';
import * as yup from 'yup';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { useDispatch } from 'react-redux';
import { loginSuccess } from '../features/auth/authSlice.js';


const loginSchema = yup.object().shape({
  email: yup.string().email('Invalid email address').required('Email is required'),
  password: yup.string().required('Password is required'),
});

export default function Login() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  // Only runs when the yup schema passes
  const onSubmit = async ({ email }) => {
    // TODO: replace with your real authentication API call, e.g.
    // const { user, token } = await api.login({ email, password });
    // Never store the password in localStorage — only the user info + token.
    const user = { email };
    const token = 'demo-token';

    dispatch(loginSuccess({ user, token }));
    navigate('/');
  };

  return (
    <AuthShell
      status="Satellite link active"
      title="Sign in to mission control"
      subtitle="Monitor your fields with satellite insights."
      chips={['🛰️ Satellite imagery', '🌱 Crop health', '🌦️ Climate']}
    >
      <form
        className="mt-7 space-y-5 login3d__z1"
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
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="login3d__label">
              Password
            </label>
            <a href="#forgot-password" className="login3d__link mb-1.5">
              Forgot password?
            </a>
          </div>
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

        <label htmlFor="remember-me" className="login3d__check">
          <input id="remember-me" type="checkbox" />
          Remember me for 30 days
        </label>

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
