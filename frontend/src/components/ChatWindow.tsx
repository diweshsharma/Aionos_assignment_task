import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, ShieldAlert, BookOpen, Sparkles } from 'lucide-react';
import type { ChatMessage } from '../types';

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
  quickPrompts: string[];
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  quickPrompts,
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
      <div className="messages-feed" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-state">
            <Bot size={40} color="var(--accent-cyan)" style={{ marginBottom: 12, opacity: 0.6 }} />
            <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
              Airline Disruption Resolution Assistant
            </p>
            <p>Select a passenger preset above or type a request to get started.</p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message-bubble ${msg.sender}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {msg.sender === 'agent' ? (
                <>
                  <Bot size={13} color="var(--accent-cyan)" />
                  <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>AI Resolution Agent</span>
                </>
              ) : (
                <>
                  <User size={13} color="var(--accent-blue)" />
                  <span>Passenger</span>
                </>
              )}
              <span>•</span>
              <span>{msg.timestamp}</span>
            </div>

            <div className="bubble-content">
              {msg.text}

              {/* Policy Cites */}
              {msg.policy_cites && msg.policy_cites.length > 0 && (
                <div className="policy-cite-box">
                  <div className="policy-cite-header">
                    <BookOpen size={13} />
                    <span>Policy Rules Applied:</span>
                  </div>
                  <ul style={{ paddingLeft: 16, margin: 0 }}>
                    {msg.policy_cites.map((cite, idx) => (
                      <li key={idx}>{cite}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Escalations Alert */}
              {msg.escalations && msg.escalations.length > 0 && (
                <div className="escalation-alert-badge">
                  <ShieldAlert size={20} style={{ flexShrink: 0, marginTop: 2, color: '#f43f5e' }} />
                  <div>
                    <div className="escalation-alert-title">
                      Escalated to Human Supervisor
                    </div>
                    {msg.escalations.map((esc, i) => (
                      <div key={i} style={{ marginTop: 2 }}>
                        • {esc.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-bubble agent">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
              <Bot size={13} />
              <span>Evaluating Policy & Actions...</span>
            </div>
            <div className="bubble-content" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={16} className="spin-icon" style={{ animation: 'spin 1.5s linear infinite' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Processing disruption resolution...</span>
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
          placeholder="Ask for refund, rebooking, lounge pass, hotel, or waiver..."
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
