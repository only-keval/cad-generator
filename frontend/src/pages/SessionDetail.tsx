import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { Session, SessionHistoryItem, RequestCreated, RequestStatus } from '../api/types';
import ChatInput from '../components/ChatInput';
import RequestCard from '../components/RequestCard';
import STLViewer from '../components/STLViewer';
import StageProgress from '../components/StageProgress';

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const [session, setSession] = useState<Session | null>(null);
  const [history, setHistory] = useState<SessionHistoryItem[]>([]);
  const [activeUrl, setActiveUrl] = useState<string | null>(null);
  const [viewingRequestId, setViewingRequestId] = useState<number | null>(null);
  const [lastCompletedUrl, setLastCompletedUrl] = useState<string | null>(null);
  const [lastCompletedId, setLastCompletedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [pollId, setPollId] = useState<number | null>(null);
  const [pollStatus, setPollStatus] = useState<RequestStatus | null>(null);
  const pollTimer = useRef<number | null>(null);
  const pollDelay = useRef(1000);
  const cancelled = useRef(false);

  const historyEndRef = useRef<HTMLDivElement>(null);

  const loadSession = useCallback(async () => {
    try {
      const s = await api.get<Session>(`/sessions/${sessionId}`);
      setSession(s);
    } catch {
      setError('Failed to load session');
    }
  }, [sessionId]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get<{ items: SessionHistoryItem[] }>(
        `/sessions/${sessionId}/history?order=asc&limit=100`,
      );
      setHistory(res.items);
      const lastDone = [...res.items].reverse().find((i: SessionHistoryItem) => i.status === 'completed');
      if (lastDone) {
        setLastCompletedId(lastDone.request_id);
        const status = await api.get<RequestStatus>(`/requests/${lastDone.request_id}`);
        if (status.result?.artifact_url) {
          setLastCompletedUrl(status.result.artifact_url);
          if (!activeUrl) setActiveUrl(status.result.artifact_url);
        }
      }
    } catch {
      // ignore
    }
  }, [sessionId, activeUrl]);

  useEffect(() => {
    loadSession();
    loadHistory();
  }, [loadSession, loadHistory]);

  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const startPolling = useCallback((requestId: number) => {
    cancelled.current = false;
    pollDelay.current = 1000;
    setPollId(requestId);
    setPollStatus(null);

    const poll = async () => {
      if (cancelled.current) return;
      try {
        const data = await api.get<RequestStatus>(`/requests/${requestId}`);
        setPollStatus(data);
        if (data.status === 'completed' || data.status === 'failed') {
          setPollId(null);
          loadHistory();
          if (data.status === 'completed' && data.result?.artifact_url) {
            setLastCompletedUrl(data.result.artifact_url);
            setLastCompletedId(requestId);
            setActiveUrl(data.result.artifact_url);
            setViewingRequestId(null);
          }
          return;
        }
      } catch {
        // ignore
      }
      if (!cancelled.current) {
        pollTimer.current = window.setTimeout(poll, pollDelay.current);
        pollDelay.current = Math.min(pollDelay.current * 1.5, 5000);
      }
    };

    poll();
  }, [loadHistory]);

  useEffect(() => {
    return () => {
      cancelled.current = true;
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, []);

  const handleSubmitPrompt = useCallback(async (prompt: string) => {
    try {
      const res = await api.post<RequestCreated>(
        `/sessions/${sessionId}/requests`,
        { prompt },
      );
      startPolling(res.request_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to submit');
    }
  }, [sessionId, startPolling]);

  const handleRetry = useCallback(async (requestId: number) => {
    try {
      const res = await api.post<RequestCreated>(
        `/requests/${requestId}/retry`,
      );
      startPolling(res.request_id);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Retry failed');
    }
  }, [startPolling]);

  const handleViewArtifact = useCallback(async (requestId: number) => {
    try {
      const status = await api.get<RequestStatus>(`/requests/${requestId}`);
      if (status.result?.artifact_url) {
        setActiveUrl(status.result.artifact_url);
        setViewingRequestId(requestId);
      }
    } catch {
      // ignore
    }
  }, []);

  const handleBackToLatest = () => {
    if (lastCompletedUrl) {
      setActiveUrl(lastCompletedUrl);
      setViewingRequestId(null);
    }
  };

  const isGenerating = pollId !== null;
  const lastFailed = history.length > 0 && history[history.length - 1].status === 'failed';
  const isViewingOld = viewingRequestId !== null && viewingRequestId !== lastCompletedId;

  if (error) return <div className="error">{error}</div>;
  if (!session) return <div className="loading">Loading session...</div>;

  return (
    <div className="page session-detail">
      <header className="page-header">
        <a href="/sessions" className="back-link">← Sessions</a>
        <h2>{session.title || `Session #${session.session_id}`}</h2>
      </header>

      <div className="session-layout">
        <div className="history-panel">
          <h3>History</h3>
          <div className="history-list">
            {history.length === 0 && !isGenerating && (
              <div className="empty-state">No requests yet.</div>
            )}
            {history.map((item) => (
              <RequestCard
                key={item.request_id}
                item={item}
                onViewArtifact={handleViewArtifact}
                onRetry={handleRetry}
                isPolling={pollId !== null}
              />
            ))}
            {isGenerating && (
              <div className="request-card generating-card">
                <div className="request-header">
                  <span className="status-badge" style={{ background: '#eab308' }}>
                    Running
                  </span>
                </div>
                <p className="request-prompt">{pollStatus?.prompt || '...'}</p>
                <StageProgress status={pollStatus} compact />
              </div>
            )}
            <div ref={historyEndRef} />
          </div>
        </div>

        <div className="main-panel">
          <div className="viewer-area">
            {isViewingOld && (
              <div className="viewer-banner">
                <span>Viewing older model (request #{viewingRequestId})</span>
                <button className="btn btn-small" onClick={handleBackToLatest}>
                  Back to latest
                </button>
              </div>
            )}
            {activeUrl ? (
              <div className="viewer-with-overlay">
                <STLViewer url={activeUrl} />
                {isGenerating && (
                  <div className="viewer-stage-overlay">
                    <StageProgress status={pollStatus} fullCard />
                  </div>
                )}
              </div>
            ) : isGenerating ? (
              <div className="viewer-placeholder generating">
                <StageProgress status={pollStatus} />
              </div>
            ) : (
              <div className="viewer-placeholder">
                <p>Submit a prompt to generate a 3D model</p>
              </div>
            )}
          </div>

          <div className="input-area">
            {lastFailed && !isGenerating && (
              <div className="retry-bar">
                <span className="retry-icon">⚠</span>
                <span>Last request failed.</span>
                <button
                  className="btn btn-retry"
                  onClick={() => handleRetry(history[history.length - 1].request_id)}
                >
                  Retry
                </button>
              </div>
            )}
            <ChatInput
              disabled={isGenerating}
              activePrompt={pollStatus?.prompt}
              onSend={handleSubmitPrompt}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
