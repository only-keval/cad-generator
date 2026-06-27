import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/auth';
import { Session } from '../api/types';

export default function SessionList() {
  const { user, clearAuth } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get<Session[]>('/sessions')
      .then(setSessions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const createSession = async () => {
    try {
      const s = await api.post<Session>('/sessions', {});
      navigate(`/sessions/${s.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create session');
    }
  };

  if (loading) return <div className="loading">Loading sessions...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="page session-list-page">
      <header className="page-header">
        <h1>CAD Generator</h1>
        <div className="header-right">
          <span className="user-badge">{user?.name}</span>
          <button className="btn btn-small" onClick={clearAuth}>Sign Out</button>
          <button className="btn btn-primary" onClick={createSession}>
            New Session
          </button>
        </div>
      </header>

      {sessions.length === 0 ? (
        <div className="empty-state">
          <p>No sessions yet. Create your first one!</p>
        </div>
      ) : (
        <div className="session-cards">
          {sessions.map((s) => (
            <div
              key={s.session_id}
              className="session-card"
              onClick={() => navigate(`/sessions/${s.session_id}`)}
            >
              <h3>{s.title || `Session #${s.session_id}`}</h3>
              <span className="session-date">
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
