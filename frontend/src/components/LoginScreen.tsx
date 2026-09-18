import React, { useState } from 'react';
import { Plane, Search, AlertCircle, ArrowRight, UserCheck } from 'lucide-react';
import { lookupPNR } from '../api/client';
import type { PNRLookupResult } from '../api/client';

interface LoginScreenProps {
  onSuccess: (data: PNRLookupResult) => void;
  onOpenAdmin: () => void;
}

const PRESET_PNRS = [
  { pnr: 'SK4821X', name: 'Priya Nair', tier: 'Gold', status: 'CANCELLED' },
  { pnr: 'TR1190B', name: 'Arvind Kulkarni', tier: 'Silver', status: 'DELAYED (4h)' },
  { pnr: 'WL7742', name: 'Meher Kaur', tier: 'Platinum', status: 'DELAYED (6h)' },
];

export const LoginScreen: React.FC<LoginScreenProps> = ({ onSuccess, onOpenAdmin }) => {
  const [pnr, setPnr] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLookup = async (inputPnr: string) => {
    const cleanPnr = inputPnr.trim().toUpperCase();
    if (!cleanPnr) {
      setError('Please enter a valid PNR code.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await lookupPNR(cleanPnr);
      onSuccess(result);
    } catch (err: any) {
      setError(err.message || `No booking found for PNR '${cleanPnr}'. Please check and try again.`);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLookup(pnr);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      background: 'radial-gradient(circle at 50% 30%, rgba(56, 189, 248, 0.12) 0%, transparent 60%), #090d16',
    }}>
      <div style={{
        width: '100%',
        maxWidth: 480,
        background: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 24,
        padding: '36px 32px',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 10 }}>
          <div style={{
            width: 52,
            height: 52,
            borderRadius: 16,
            background: 'linear-gradient(135deg, #38bdf8, #6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            boxShadow: '0 8px 25px rgba(56, 189, 248, 0.3)',
          }}>
            <Plane size={28} />
          </div>

          <h1 style={{
            fontSize: '1.45rem',
            fontWeight: 800,
            background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}>
            AIONOS SkyAssist
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
            Enter your PNR code to access instant support.
          </p>
        </div>

        {/* Error Notification */}
        {error && (
          <div style={{
            padding: '12px 16px',
            borderRadius: 12,
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#fca5a5',
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="form-label" style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
              Booking Reference (PNR)
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={18} style={{ position: 'absolute', left: 14, color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="e.g. SK4821X, TR1190B, WL7742"
                value={pnr}
                onChange={(e) => {
                  setPnr(e.target.value.toUpperCase());
                  setError(null);
                }}
                style={{
                  width: '100%',
                  paddingLeft: 42,
                  fontSize: '1rem',
                  letterSpacing: '0.05em',
                  fontFamily: 'var(--font-mono)',
                  height: 48,
                  borderRadius: 12,
                }}
                autoFocus
              />
            </div>
          </div>

          <button
            type="submit"
            className="submit-btn"
            disabled={loading || !pnr.trim()}
            style={{
              height: 48,
              borderRadius: 12,
              fontSize: '0.95rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            {loading ? (
              <span>Looking up PNR...</span>
            ) : (
              <>
                <span>Continue to Resolution Console</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {/* Quick Presets Bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 8, borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', fontWeight: 600 }}>
            Demo Quick Selection Presets:
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
            {PRESET_PNRS.map((item) => (
              <button
                key={item.pnr}
                type="button"
                onClick={() => {
                  setPnr(item.pnr);
                  handleLookup(item.pnr);
                }}
                className="preset-btn"
                style={{
                  background: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 10,
                  padding: '6px 12px',
                  fontSize: '0.78rem',
                }}
              >
                <UserCheck size={13} color="var(--accent-cyan)" />
                <span style={{ color: '#fff' }}>{item.name}</span>
                <span className={`tier-badge tier-${item.tier}`}>{item.tier}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Footer Admin Link */}
        <div style={{ textAlign: 'center', marginTop: 4 }}>
          <button
            type="button"
            onClick={onOpenAdmin}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-indigo)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Admin Portal (Add New Customer / CSV Upload)
          </button>
        </div>
      </div>
    </div>
  );
};
