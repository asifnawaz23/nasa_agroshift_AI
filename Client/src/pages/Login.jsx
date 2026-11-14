import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // Add your authentication API call here
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <span className="text-2xl font-bold tracking-wider text-indigo-600">
          AppPanel
        </span>
        <h2 className="mt-4 text-2xl font-bold text-gray-900">
          Sign in to your account
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Welcome back! Please enter your details.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 border border-gray-200 rounded-xl shadow-xs sm:px-10">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-1.5 block w-full px-3.5 py-2 text-sm text-gray-900 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-700"
                >
                  Password
                </label>
                <a
                  href="#forgot-password"
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-500"
                >
                  Forgot password?
                </a>
              </div>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1.5 block w-full px-3.5 py-2 text-sm text-gray-900 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center">
              <input
                id="remember-me"
                type="checkbox"
                className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label
                htmlFor="remember-me"
                className="ml-2 block text-sm text-gray-600"
              >
                Remember me for 30 days
              </label>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition cursor-pointer"
            >
              Sign in
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-600">
            Don&apos;t have an account?{' '}
            <Link
              to="/signup"
              className="font-semibold text-indigo-600 hover:text-indigo-500"
            >
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}