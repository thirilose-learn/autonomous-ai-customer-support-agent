import React from 'react';

export function StatusBadge({ status, error, onRetry }) {
  if (status === 'loading') {
    return (
      <div className="status-badge loading" title="Contacting FastAPI backend...">
        <span className="status-dot"></span>
        <span>Checking Backend...</span>
      </div>
    );
  }

  if (status === 'connected') {
    return (
      <div className="status-badge connected" title="FastAPI backend is responsive and healthy">
        <span className="status-dot"></span>
        <span>Backend Connected</span>
      </div>
    );
  }

  return (
    <div className="status-badge disconnected" title={error || "Cannot reach backend"}>
      <span className="status-dot"></span>
      <span>Backend Disconnected</span>
      {onRetry && (
        <button className="retry-btn" onClick={onRetry} title="Click to retry health check">
          Retry
        </button>
      )}
    </div>
  );
}
