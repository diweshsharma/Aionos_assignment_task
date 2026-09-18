import React from 'react';
import { Plane, UserCheck, PlusCircle, Activity, LogOut } from 'lucide-react';
import type { Customer } from '../types';

interface HeaderProps {
  customer?: Customer | null;
  activePnr: string;
  onLogout: () => void;
  onOpenAdmin: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  customer,
  activePnr,
  onLogout,
  onOpenAdmin,
}) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon">
          <Plane size={22} />
        </div>
        <div>
          <div className="brand-title">AIONOS SkyAssist</div>
          <div className="brand-subtitle">Disruption Resolution Agent</div>
        </div>
      </div>

      {activePnr && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'rgba(15, 23, 42, 0.7)',
          padding: '6px 14px',
          borderRadius: 12,
          border: '1px solid var(--border-subtle)',
        }}>
          <UserCheck size={16} color="var(--accent-cyan)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#fff' }}>
                {customer?.name || `Passenger (${activePnr})`}
              </span>
              {customer?.loyalty_tier && (
                <span className={`tier-badge tier-${customer.loyalty_tier}`}>
                  {customer.loyalty_tier}
                </span>
              )}
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              PNR: {activePnr}
            </span>
          </div>

          <button
            onClick={onLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '4px 8px',
              borderRadius: 6,
              border: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-secondary)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              marginLeft: 6,
            }}
            title="Switch PNR / Logout"
          >
            <LogOut size={12} />
            <span>Switch PNR</span>
          </button>
        </div>
      )}

      <div className="header-actions">
        <div className="status-badge">
          <span className="status-dot"></span>
          <Activity size={12} style={{ marginRight: 2 }} />
          <span>System Active</span>
        </div>

        <button className="admin-btn" onClick={onOpenAdmin}>
          <PlusCircle size={15} />
          <span>Admin Portal</span>
        </button>
      </div>
    </header>
  );
};
