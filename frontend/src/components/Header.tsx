import React from 'react';
import { Plane, UserCheck, PlusCircle, Activity } from 'lucide-react';
import type { PresetCustomer } from '../types';

interface HeaderProps {
  presets: PresetCustomer[];
  activePnr: string;
  onSelectPreset: (preset: PresetCustomer) => void;
  onOpenAdmin: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  presets,
  activePnr,
  onSelectPreset,
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

      <div className="presets-group">
        {presets.map((p) => {
          const isActive = p.pnr === activePnr;
          return (
            <button
              key={p.pnr}
              onClick={() => onSelectPreset(p)}
              className={`preset-btn ${isActive ? 'active' : ''}`}
              title={p.description}
            >
              <UserCheck size={14} />
              <span>{p.label}</span>
              <span className={`tier-badge tier-${p.tier}`}>{p.tier}</span>
            </button>
          );
        })}
      </div>

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
