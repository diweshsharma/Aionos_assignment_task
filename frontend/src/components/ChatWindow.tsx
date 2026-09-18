import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Flag, Sparkles, SlidersHorizontal } from 'lucide-react';
import type { ChatMessage } from '../types';

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  quickPrompts: string[];
  onToggleDetails: () => void;
  isDetailsOpen: boolean;
  actionsCount: number;
  escalationsCount: number;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  quickPrompts,
  onToggleDetails,
  isDetailsOpen,
  actionsCount,
  escalationsCount,
}) => {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleChipClick = (prompt: string) => {
    if (isLoading) return;
    onSendMessage(prompt);
  };

  return (
    <div className="chat-container">
      {/* Top Header Bar for Chat */}
      <div className="chat-header-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Bot size={18} color="var(--accent-cyan)" />
          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
            Support Assistant
          </span>
          <span className="online-indicator-pill">Online</span>
        </div>

        <button
          className={`details-toggle-btn ${isDetailsOpen ? 'active' : ''}`}
          onClick={onToggleDetails}
          title="Toggle operational logs & profile"
        >
          <SlidersHorizontal size={14} />
          <span>Disruption Details</span>
          {(actionsCount > 0 || escalationsCount > 0) && (
            <span className="details-badge">
              {actionsCount + escalationsCount}
            </span>
          )}
        </button>
      </div>

      <div className="messages-feed" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-state">
            <Bot size={40} color="var(--accent-cyan)" style={{ marginBottom: 12, opacity: 0.6 }} />
            <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
              Airline Disruption Resolution Assistant
            </p>
            <p>Connecting to your flight context...</p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message-bubble ${msg.sender}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              {msg.sender === 'agent' ? (
                <>
                  <Bot size={13} color="var(--accent-cyan)" />
                  <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>AIONOS Support Agent</span>
                </>
              ) : (
                <>
                  <User size={13} color="var(--accent-blue)" />
                  <span>You</span>
                </>
              )}
              <span>•</span>
              <span>{msg.timestamp}</span>
            </div>

            <div className="bubble-content">
              {msg.text}

              {/* Subtle inline escalation marker (no raw JSON/policy reasoning) */}
              {msg.escalations && msg.escalations.length > 0 && (
                <div className="subtle-escalation-tag">
                  <Flag size={12} color="#f43f5e" />
                  <span>Escalated to a supervisor</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-bubble agent">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--accent-cyan)', marginBottom: 4 }}>
              <Bot size={13} />
              <span>AIONOS Support Agent</span>
            </div>
            <div className="bubble-content" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={16} className="spin-icon" style={{ animation: 'spin 1.5s linear infinite' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Checking options...</span>
            </div>
          </div>
        )}
      </div>

      {/* Quick Prompts */}
      {quickPrompts.length > 0 && (
        <div className="quick-prompts-container">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontWeight: 600 }}>
            Suggested:
          </span>
          {quickPrompts.map((p, idx) => (
            <button key={idx} className="quick-prompt-chip" onClick={() => handleChipClick(p)}>
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input Form */}
      <form className="chat-input-wrapper" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          placeholder="Ask a question or request assistance..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};

