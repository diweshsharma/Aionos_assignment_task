import React from 'react';
import { ShieldAlert, CheckCircle, Ticket, Hotel, Coffee, RotateCcw, User, History, X } from 'lucide-react';
import type { ActionItem, EscalationItem, Customer, Booking } from '../types';

interface ActionLogPanelProps {
  isOpen: boolean;
  onClose: () => void;
  actions: ActionItem[];
  escalations: EscalationItem[];
  customer?: Customer | null;
  booking?: Booking | null;
}

export const ActionLogPanel: React.FC<ActionLogPanelProps> = ({
  isOpen,
  onClose,
  actions,
  escalations,
  customer,
}) => {
  if (!isOpen) return null;

  const renderActionIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('meal')) return <Coffee size={15} color="var(--accent-cyan)" />;
    if (t.includes('lounge')) return <Ticket size={15} color="#f59e0b" />;
    if (t.includes('hotel')) return <Hotel size={15} color="#a855f7" />;
    if (t.includes('rebook') || t.includes('refund')) return <RotateCcw size={15} color="#10b981" />;
    return <CheckCircle size={15} color="var(--accent-cyan)" />;
  };

  const getActionTitle = (act: ActionItem): string => {
    const t = act.type.toLowerCase();
    const details = act.details || {};
    if (t.includes('meal_voucher')) {
      const amt = details.amount_inr || 500;
      return `Meal Voucher Issued — ₹${amt}`;
    }
    if (t.includes('lounge_access')) {
      return 'Airport Lounge Access Granted';
    }
    if (t.includes('hotel_provided') || t.includes('hotel')) {
      const hours = details.delay_hours ? `${details.delay_hours}h` : 'delayed hours';
      return `Hotel Accommodation (${hours})`;
    }
    if (t.includes('full_refund')) {
      return 'Full Refund Option to Original Payment';
    }
    if (t.includes('free_rebook')) {
      return 'Free Flight Rebooking Option';
    }
    if (t.includes('fare_difference_waived')) {
      const amt = details.amount_inr || 2000;
      return `Fare Difference Waived (₹${amt})`;
    }
    if (t.includes('escalation')) {
      return 'Escalation Flagged for Supervisor';
    }
    return act.type.replace(/_/g, ' ');
  };

  return (
    <div className="details-drawer-overlay" onClick={onClose}>
      <div className="details-drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <History size={18} color="var(--accent-cyan)" />
            <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>
              Disruption & Account Details
            </span>
          </div>
          <button className="drawer-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Customer Profile Section */}
          <div className="panel-card">
            <div className="card-header">
              <User className="card-header-icon" size={16} />
              <span>Customer Profile</span>
            </div>
            {customer ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Passenger:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{customer.name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Loyalty Tier:</span>
                  <span className={`tier-badge tier-${customer.loyalty_tier}`}>{customer.loyalty_tier}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Flights (Last 12m):</span>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{customer.flights_last_12mo}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Prior Complaints:</span>
                  <span style={{ fontWeight: 600, color: customer.prior_complaints?.length ? 'var(--status-amber)' : 'var(--text-secondary)' }}>
                    {customer.prior_complaints?.length || 0} recorded
                  </span>
                </div>
              </div>
            ) : (
              <div className="empty-state">No active customer profile loaded</div>
            )}
          </div>

          {/* Pending Supervisor Escalations */}
          {escalations.length > 0 && (
            <div className="panel-card" style={{ borderColor: 'rgba(244, 63, 94, 0.3)', background: 'rgba(244, 63, 94, 0.04)' }}>
              <div className="card-header" style={{ color: '#f43f5e' }}>
                <ShieldAlert size={16} />
                <span>Pending Supervisor Reviews ({escalations.length})</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {escalations.map((esc, i) => (
                  <div key={i} className="plain-escalation-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span className="pending-review-badge">Pending Supervisor Review</span>
                      <span className="action-time">{esc.timestamp}</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                      {esc.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* System Actions History */}
          <div className="panel-card">
            <div className="card-header">
              <CheckCircle className="card-header-icon" size={16} />
              <span>Processed Actions ({actions.length})</span>
            </div>

            {actions.length === 0 ? (
              <div className="empty-state">
                No system actions executed yet.
              </div>
            ) : (
              <div className="action-items-list">
                {actions.map((act, index) => (
                  <div key={index} className="plain-action-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {renderActionIcon(act.type)}
                        <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                          {getActionTitle(act)}
                        </span>
                      </div>
                      <span className="action-time">{act.timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionLogPanel;

