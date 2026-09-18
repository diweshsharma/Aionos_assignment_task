import React from 'react';
import { ShieldAlert, CheckCircle, Ticket, Hotel, Coffee, RotateCcw, AlertTriangle, User, History } from 'lucide-react';
import type { ActionItem, EscalationItem, Customer, Booking } from '../types';

interface ActionLogPanelProps {
  actions: ActionItem[];
  escalations: EscalationItem[];
  customer?: Customer | null;
  booking?: Booking | null;
}

export const ActionLogPanel: React.FC<ActionLogPanelProps> = ({
  actions,
  escalations,
  customer,
}) => {
  const renderActionIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'meal_voucher':
      case 'meal_voucher_500':
        return <Coffee size={14} color="#38bdf8" />;
      case 'lounge_access':
        return <Ticket size={14} color="#f59e0b" />;
      case 'hotel_voucher':
      case 'hotel_delayed_hours':
        return <Hotel size={14} color="#a855f7" />;
      case 'rebooking_option':
        return <RotateCcw size={14} color="#10b981" />;
      default:
        return <CheckCircle size={14} color="#38bdf8" />;
    }
  };

  return (
    <div className="audit-panel">
      {/* Customer Profile Card */}
      <div className="panel-card">
        <div className="card-header">
          <User className="card-header-icon" size={16} />
          <span>Customer Profile</span>
        </div>

        {customer ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Loyalty Tier:</span>
              <span className={`tier-badge tier-${customer.loyalty_tier}`}>{customer.loyalty_tier}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Flights (Last 12m):</span>
              <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{customer.flights_last_12mo}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Prior Complaints:</span>
              <span style={{ fontWeight: 600, color: customer.prior_complaints?.length ? 'var(--status-amber)' : 'var(--text-secondary)' }}>
                {customer.prior_complaints?.length || 0} recorded
              </span>
            </div>
          </div>
        ) : (
          <div className="empty-state">No active customer loaded</div>
        )}
      </div>

      {/* Escalation Queue Card */}
      {escalations.length > 0 && (
        <div className="panel-card" style={{ borderColor: 'rgba(244, 63, 94, 0.4)', background: 'rgba(244, 63, 94, 0.05)' }}>
          <div className="card-header" style={{ color: '#f43f5e' }}>
            <ShieldAlert size={16} />
            <span>Human Supervisor Queue ({escalations.length})</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {escalations.map((esc, i) => (
              <div key={i} style={{
                padding: '10px 12px',
                borderRadius: 8,
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.25)',
                fontSize: '0.8rem',
                color: '#fca5a5'
              }}>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>Escalation Flagged</div>
                <div>{esc.reason}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>{esc.timestamp}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Executed Actions Log Card */}
      <div className="panel-card" style={{ flex: 1 }}>
        <div className="card-header">
          <History className="card-header-icon" size={16} />
          <span>Executed Actions ({actions.length})</span>
        </div>

        {actions.length === 0 ? (
          <div className="empty-state">
            No system actions executed yet for this session.
          </div>
        ) : (
          <div className="action-items-list">
            {actions.map((act, index) => (
              <div key={index} className={`action-item-card ${act.escalated ? 'escalated' : ''}`}>
                <div className="action-item-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {renderActionIcon(act.type)}
                    <span className="action-type-label">{act.type}</span>
                  </div>
                  <span className="action-time">{act.timestamp}</span>
                </div>

                <div className="action-details-json">
                  {JSON.stringify(act.details, null, 2)}
                </div>

                {act.escalated && (
                  <div style={{ fontSize: '0.72rem', color: '#f43f5e', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertTriangle size={12} />
                    <span>Requires Supervisor Authorization</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
