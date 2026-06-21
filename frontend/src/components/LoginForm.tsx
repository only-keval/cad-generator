import { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../store/auth';

interface AuthResponse {
  token: string;
  user_id: number;
  name: string;
  email: string | null;
  is_guest: boolean;
}

type Mode = 'login' | 'signup' | 'loading';

export default function LoginForm() {
  const { token, setAuth } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (token) return null;

  const handleExisting = async () => {
    setMode('loading');
    setError(null);
    try {
      if (mode === 'login') {
        const res = await api.post<AuthResponse>('/auth/login', { email, password });
        setAuth(res.token, res);
      } else {
        const res = await api.post<AuthResponse>('/auth/signup', { name, email, password });
        setAuth(res.token, res);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Request failed');
      setMode(mode);
    }
  };

  const handleGuest = async () => {
    setError(null);
    try {
      const res = await api.post<AuthResponse>('/auth/guest');
      setAuth(res.token, res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Request failed');
    }
  };

  if (mode === 'loading') {
    return (
      <div className="modal-overlay">
        <div className="modal">
          <p>Connecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>
        <div className="auth-tabs">
          <button
            className={`auth-tab${mode === 'login' ? ' active' : ''}`}
            onClick={() => { setMode('login'); setError(null); }}
          >
            Sign In
          </button>
          <button
            className={`auth-tab${mode === 'signup' ? ' active' : ''}`}
            onClick={() => { setMode('signup'); setError(null); }}
          >
            Sign Up
          </button>
        </div>

        <div className="auth-fields">
          {mode === 'signup' && (
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
              autoFocus
            />
          )}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoFocus={mode === 'login'}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
        </div>

        {error && <p className="auth-error">{error}</p>}

        <button className="btn btn-primary btn-auth" onClick={handleExisting} disabled={!email || !password}>
          {mode === 'login' ? 'Sign In' : 'Create Account'}
        </button>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <button className="btn btn-guest" onClick={handleGuest}>
          Continue as Guest
        </button>
      </div>
    </div>
  );
}
