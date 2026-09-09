import React from 'react';

export function ChatWindow({ messages, onSelectPrompt }) {
  const quickPrompts = [
    { label: '📦 Where is my order?', text: 'Where is my order?' },
    { label: '🔄 Can I return my product?', text: 'Can I return my product after 10 days?' },
    { label: '💳 What payment method did I use?', text: 'What payment method did I use?' },
    { label: '🚨 Connect to human support', text: 'I have an unresolved issue, please escalate.' },
  ];

  return (
    <div className="chat-container">
      <div className="chat-history">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-bubble ${msg.sender}`}>
            <div className={`avatar ${msg.sender}`}>
              {msg.sender === 'assistant' ? '🤖' : '👤'}
            </div>
            <div className="message-content">
              {msg.sender === 'assistant' && (
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap' }}>
                  <div className="message-badge">AI Support Agent</div>
                  {msg.intent && (
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontWeight: '600' }}>
                      {msg.intent}
                    </span>
                  )}
                  {msg.latency_ms && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                      ⚡ {msg.latency_ms}ms
                    </span>
                  )}
                </div>
              )}
              {msg.tools_executed && msg.tools_executed.length > 0 && (
                <div style={{ display: 'flex', gap: '6px', margin: '4px 0 8px 0', flexWrap: 'wrap' }}>
                  {msg.tools_executed.map((toolName, tIdx) => (
                    <span key={tIdx} style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontFamily: 'monospace' }}>
                      🔧 {toolName}
                    </span>
                  ))}
                </div>
              )}
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>

              {msg.isWelcome && (
                <div className="architecture-cards">
                  <div className="arch-card">
                    <div className="arch-card-title">📊 Structured Data</div>
                    <div className="arch-card-desc">
                      Queries orders, items, products & payments from Supabase PostgreSQL.
                    </div>
                  </div>
                  <div className="arch-card">
                    <div className="arch-card-title">📚 Knowledge RAG</div>
                    <div className="arch-card-desc">
                      Retrieves return, refund & shipping policies using LlamaIndex + pgvector.
                    </div>
                  </div>
                  <div className="arch-card">
                    <div className="arch-card-title">🛡️ Guardrails & Fallback</div>
                    <div className="arch-card-desc">
                      Validates answers and creates escalation tickets for human support.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="quick-prompts">
        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginRight: '4px' }}>
          Test Scenarios:
        </span>
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            className="prompt-chip"
            onClick={() => onSelectPrompt(p.text)}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
