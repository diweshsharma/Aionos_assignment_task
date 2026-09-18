import React, { useState } from 'react';
import { X, CheckCircle2, AlertCircle } from 'lucide-react';
import { addCustomer, addBooking, importCSV } from '../api/client';

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (pnr: string) => void;
}

export const AdminModal: React.FC<AdminModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [tab, setTab] = useState<'single' | 'csv'>('single');
  const [name, setName] = useState('Rahul Sharma');
  const [loyaltyTier, setLoyaltyTier] = useState<'Silver' | 'Gold' | 'Platinum' | 'Standard' | 'Base'>('Gold');
  const [pnr, setPnr] = useState('RS9988X');
  const [flightNumber, setFlightNumber] = useState('AI505');
  const [routeOrigin] = useState('DEL');
  const [routeDest] = useState('BOM');
  const [flightStatus, setFlightStatus] = useState<'CANCELLED' | 'DELAYED' | 'ON_TIME'>('DELAYED');
  const [delayHours, setDelayHours] = useState(4);

  const [custCsv, setCustCsv] = useState<File | null>(null);
  const [bookCsv, setBookCsv] = useState<File | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  const handleCreateSingle = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);

    try {
      const todayStr = new Date().toISOString().split('T')[0];

      // 1. Create Customer
      const cust = await addCustomer({
        name,
        loyalty_tier: loyaltyTier === 'Base' ? 'Standard' : loyaltyTier,
        flights_last_12mo: 5,
        contact: `${name.toLowerCase().replace(/\s+/g, '.')}@example.com`,
      });

      // 2. Create Booking linked to Customer
      await addBooking({
        pnr: pnr.toUpperCase(),
        customer_id: cust.id,
        flight_number: flightNumber,
        route_origin: routeOrigin,
        route_dest: routeDest,
        flight_date: todayStr,
        scheduled_departure: `${todayStr}T10:00:00`,
        status: flightStatus,
        delay_hours: flightStatus === 'DELAYED' ? delayHours : 0,
      });

      setStatusMsg({ type: 'success', text: `Added ${name} (PNR: ${pnr.toUpperCase()}) successfully!` });
      onSuccess(pnr.toUpperCase());
    } catch (err: any) {
      const message = typeof err === 'string'
        ? err
        : err?.response?.data?.detail
        || err?.response?.data?.message
        || err?.message
        || "Something went wrong — please check the form and try again.";
      const text = typeof message === 'object' ? JSON.stringify(message) : String(message);
      setStatusMsg({ type: 'error', text });
    } finally {
      setLoading(false);
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!custCsv && !bookCsv) {
      setStatusMsg({ type: 'error', text: 'Select at least one CSV file to upload.' });
      return;
    }

    setLoading(true);
    setStatusMsg(null);

    try {
      const res = await importCSV(custCsv || undefined, bookCsv || undefined);
      setStatusMsg({ type: 'success', text: `Import complete: ${JSON.stringify(res.report)}` });
    } catch (err: any) {
      const message = typeof err === 'string'
        ? err
        : err?.response?.data?.detail
        || err?.response?.data?.message
        || err?.message
        || "Import failed";
      const text = typeof message === 'object' ? JSON.stringify(message) : String(message);
      setStatusMsg({ type: 'error', text });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-title">Admin Data Ingestion Portal</div>
          <button className="close-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 10 }}>
          <button
            onClick={() => setTab('single')}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: 'none',
              background: tab === 'single' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              color: tab === 'single' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Add New Passenger & Booking
          </button>
          <button
            onClick={() => setTab('csv')}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: 'none',
              background: tab === 'csv' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              color: tab === 'csv' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Bulk CSV Import
          </button>
        </div>

        {statusMsg && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 8,
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
            border: `1px solid ${statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)'}`,
            color: statusMsg.type === 'success' ? '#10b981' : '#f43f5e'
          }}>
            {statusMsg.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {tab === 'single' ? (
          <form onSubmit={handleCreateSingle} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Passenger Name</label>
              <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>

            <div className="form-group">
              <label className="form-label">Loyalty Tier</label>
              <select className="form-input" value={loyaltyTier} onChange={(e: any) => setLoyaltyTier(e.target.value)}>
                <option value="Base">Base</option>
                <option value="Silver">Silver</option>
                <option value="Gold">Gold</option>
                <option value="Platinum">Platinum</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">PNR Code</label>
              <input className="form-input" value={pnr} onChange={(e) => setPnr(e.target.value)} required />
            </div>

            <div className="form-group">
              <label className="form-label">Flight Number</label>
              <input className="form-input" value={flightNumber} onChange={(e) => setFlightNumber(e.target.value)} required />
            </div>

            <div className="form-group">
              <label className="form-label">Flight Status</label>
              <select className="form-input" value={flightStatus} onChange={(e: any) => setFlightStatus(e.target.value)}>
                <option value="DELAYED">DELAYED</option>
                <option value="CANCELLED">CANCELLED</option>
                <option value="ON_TIME">ON_TIME</option>
              </select>
            </div>

            {flightStatus === 'DELAYED' && (
              <div className="form-group">
                <label className="form-label">Delay (Hours)</label>
                <input type="number" className="form-input" value={delayHours} onChange={(e) => setDelayHours(Number(e.target.value))} min={1} required />
              </div>
            )}

            <button type="submit" className="submit-btn" style={{ gridColumn: 'span 2', marginTop: 8 }} disabled={loading}>
              {loading ? 'Creating...' : 'Create & Select Passenger'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleImportCsv} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Customers CSV</label>
              <input type="file" accept=".csv" className="form-input" onChange={(e) => setCustCsv(e.target.files?.[0] || null)} />
            </div>

            <div className="form-group">
              <label className="form-label">Bookings CSV</label>
              <input type="file" accept=".csv" className="form-input" onChange={(e) => setBookCsv(e.target.files?.[0] || null)} />
            </div>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Importing...' : 'Upload & Validate CSV'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
