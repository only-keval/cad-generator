import { SessionHistoryItem } from '../api/types';

interface Props {
  item: SessionHistoryItem;
  onViewArtifact: (requestId: number) => void;
  onRetry: (requestId: number) => void;
  isPolling: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  queued: '#64748b',
  running: '#eab308',
  completed: '#22c55e',
  failed: '#ef4444',
};

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Done',
  failed: 'Failed',
};

export default function RequestCard({ item, onViewArtifact, onRetry, isPolling }: Props) {
  return (
    <div className="request-card">
      <div className="request-header">
        <span
          className="status-badge"
          style={{ background: STATUS_COLORS[item.status] || '#64748b' }}
        >
          {STATUS_LABELS[item.status] || item.status}
        </span>
        <span className="request-time">
          {new Date(item.created_at).toLocaleTimeString()}
        </span>
      </div>
      <p className="request-prompt">{item.prompt}</p>
      <div className="request-actions">
        {item.status === 'completed' && (
          <button
            className="btn btn-small"
            onClick={() => onViewArtifact(item.request_id)}
          >
            View STL
          </button>
        )}
        {item.status === 'failed' && (
          <button
            className="btn btn-small btn-retry"
            onClick={() => onRetry(item.request_id)}
            disabled={isPolling}
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
