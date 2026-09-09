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
        <div className="brand-logo">AI</div>
        <div>
          <div className="brand-title">
            Autonomous Resolution Agent
            <span className="brand-badge">RAG & Persona Ready</span>
          </div>
          <div className="brand-subtitle">
            LangChain &bull; LlamaIndex &bull; Supabase pgvector &bull; FastAPI &bull; React
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
