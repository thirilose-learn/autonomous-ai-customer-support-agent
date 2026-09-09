import React, { useState } from 'react';

export function MessageInput({ onSendMessage, disabled }) {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || disabled) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  return (
    <div className="chat-input-area">
      <form onSubmit={handleSubmit}>
        <div className="input-box-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder="Type a customer support inquiry (e.g. 'Where is my order?')..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={disabled}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={disabled || !inputText.trim()}
            title="Send Message"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </form>

      <div className="input-footer-note">
        <span>🔒 Level 1 Foundation Shell &bull; End-to-end backend connectivity verified</span>
        <span>AI Agents activate in Level 5+</span>
      </div>
    </div>
  );
}
