import React from 'react';
import { User, AlertTriangle, Clock, MapPin, Award } from 'lucide-react';
import type { Customer, Booking } from '../types';

interface CustomerBannerProps {
  customer?: Customer | null;
  booking?: Booking | null;
  fallbackPnr: string;
}

export const CustomerBanner: React.FC<CustomerBannerProps> = ({
  customer,
  booking,
  fallbackPnr,
}) => {
  const avatarStyle: React.CSSProperties = {
    width: 38,
    height: 38,
    borderRadius: '50%',
    background: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#38bdf8',
  };

  return (
    <div className="customer-banner">
      <div className="customer-info-meta">
        <div style={avatarStyle}>
          <User size={20} />
        </div>

        <div className="passenger-name-group">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="passenger-name">
              {customer?.name || (booking ? `Passenger (${fallbackPnr})` : 'Active Passenger')}
            </span>
            {customer?.loyalty_tier && (
              <span className={`tier-badge tier-${customer.loyalty_tier}`}>
                <Award size={10} style={{ marginRight: 3, verticalAlign: 'middle' }} />
                {customer.loyalty_tier}
              </span>
            )}
          </div>
          <span className="pnr-tag">PNR: {booking?.pnr || fallbackPnr}</span>
        </div>
      </div>

      {booking ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', fontSize: '0.8rem' }}>
            <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <MapPin size={12} color="var(--accent-cyan)" />
              <span>{booking.route_origin} → {booking.route_dest} ({booking.flight_number})</span>
            </div>
            {booking.delay_hours > 0 && (
              <div style={{ color: 'var(--status-amber)', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2, fontWeight: 600 }}>
                <Clock size={12} />
                <span>Delayed {booking.delay_hours} Hours</span>
              </div>
            )}
          </div>

          <div className={`flight-status-chip ${booking.status}`}>
            <AlertTriangle size={14} />
            <span>{booking.status}</span>
          </div>
        </div>
      ) : (
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Ready for queries
        </div>
      )}
    </div>
  );
};

