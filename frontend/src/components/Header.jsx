import React from 'react';
import { StatusBadge } from './StatusBadge';
import { PersonaSelector } from './PersonaSelector';

export function Header({
  backendStatus,
  backendError,
  onRetryBackend,
  personas = [],
  selectedPersona = null,
  personaLoading = false,
  personaError = null,
  onSelectPersona = () => {},
}) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <div>
          <div className="brand-title">
            Customer Support Agent
            <span className="brand-badge">24/7 AI Care</span>
          </div>
          <div className="brand-subtitle">
            Instant help with orders, deliveries, returns & store policies
          </div>
        </div>
      </div>

      <div className="header-controls">
        <PersonaSelector
          personas={personas}
          selectedPersona={selectedPersona}
          loading={personaLoading}
          error={personaError}
          onSelectPersona={onSelectPersona}
        />

        <StatusBadge
          status={backendStatus}
          error={backendError}
          onRetry={onRetryBackend}
        />
      </div>
    </header>
  );
}
