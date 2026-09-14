import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function ChatWindow({ messages, isAgentResponding, onSelectPrompt }) {
  const messagesEndRef = useRef(null);

  const quickPrompts = [
    { label: '📦 Track my order', text: 'Where is my order?' },
    { label: '🔄 Return & refund policy', text: 'What is your refund and return policy?' },
    { label: '💳 Payment methods', text: 'What payment method was used for my orders?' },
    { label: '🎫 Request supervisor review', text: 'I need to speak with a supervisor regarding an issue.' },
  ];

  // Smoothly scroll down when messages change or agent is responding
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAgentResponding]);

  const formatIntent = (intent) => {
    switch (intent) {
      case 'ORDER_INQUIRY':
        return '📦 Order Inquiry';
      case 'POLICY_RAG':
        return '📚 Store Policy';
      case 'ESCALATION':
        return '🎫 Human Escalation';
      case 'GENERAL_SUPPORT':
        return '💬 Support Help';
      case 'GENERAL_CONVERSATION':
        return '💬 Conversation';
      default:
        return intent;
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-history">
        {messages.map((msg) => {
          const ticketMatch = msg.text?.match(/ESC-[A-F0-9]{8}/);
          const ticketId = ticketMatch ? ticketMatch[0] : null;

          return (
            <div key={msg.id} className={`message-bubble ${msg.sender} ${msg.isError ? 'error-bubble' : ''}`}>
              <div className={`avatar ${msg.sender}`}>
                {msg.sender === 'assistant' ? '🤖' : '👤'}
              </div>

              <div className="message-content">
                {msg.sender === 'assistant' && (
                  <div className="agent-meta-header">
                    <span className="agent-label">Support Assistant</span>
                    {msg.intent && (
                      <span className="agent-intent-pill">
                        {formatIntent(msg.intent)}
                      </span>
                    )}
                  </div>
                )}

                {msg.sender === 'assistant' ? (
                  <div className="markdown-content">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ node, ...props }) => (
                          <div className="markdown-table-wrapper">
                            <table {...props} />
                          </div>
                        ),
                        a: ({ node, ...props }) => (
                          <a {...props} target="_blank" rel="noopener noreferrer" />
                        ),
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div className="user-text-content">{msg.text}</div>
                )}

                {msg.sender === 'assistant' && msg.tools_executed && msg.tools_executed.length > 0 && (
                  <div className="resolution-trust-badge" title={`Verified with tools: ${msg.tools_executed.join(', ')}`}>
                    <span className="trust-check" aria-hidden="true">✓</span>
                    <span>Verified via customer account records</span>
                  </div>
                )}

                {ticketId && (
                  <div className="escalation-notice-card">
                    <div className="escalation-card-header">
                      <span className="esc-icon">🎫</span>
                      <span className="esc-title">Escalation Ticket Logged</span>
                      <span className="esc-id-tag">{ticketId}</span>
                    </div>
                    <p className="esc-description">
                      Your issue has been recorded in the support queue. A human representative will review your case using your provided contact details.
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isAgentResponding && (
          <div className="message-bubble assistant typing-bubble">
            <div className="avatar assistant">🤖</div>
            <div className="message-content typing-content">
              <div className="agent-meta-header">
                <span className="agent-label">Support Agent</span>
                <span className="agent-intent-pill analyzing">Searching records...</span>
              </div>
              <div className="typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="quick-prompts">
        <span className="prompts-label">Quick Inquiries:</span>
        <div className="prompts-scroll-wrapper">
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              className="prompt-chip"
              onClick={() => onSelectPrompt(p.text)}
              disabled={isAgentResponding}
              title={`Ask: "${p.text}"`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

