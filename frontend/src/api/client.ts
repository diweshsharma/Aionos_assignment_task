import type { ChatResponse, Customer, Booking } from '../types';

const BASE_URL = 'http://localhost:8000';
let authToken = 'dev_secret_token_123'; // Matches AUTH_TOKEN in .env

export const setAuthToken = (token: string) => {
  authToken = token;
};

export const getAuthToken = () => authToken;

export async function loginWithToken(token: string): Promise<boolean> {
  try {
    const formData = new URLSearchParams();
    formData.append('token', token);
    
    const res = await fetch(`${BASE_URL}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
    
    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token || token;
      return true;
    }
    return false;
  } catch (err) {
    console.error('Auth login failed:', err);
    return false;
  }
}

export interface PNRLookupResult {
  customer_id: number;
  name: string;
  loyalty_tier: 'Silver' | 'Gold' | 'Platinum' | 'Base';
  pnr: string;
  contact?: string;
  flights_last_12mo: number;
  prior_complaints: any[];
  booking: Booking;
}

function formatErrorMessage(detail: any, defaultMsg: string): string {
  if (!detail) return defaultMsg;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => {
        if (typeof d === 'string') return d;
        if (d.msg) {
          const locStr = Array.isArray(d.loc) ? d.loc.filter((l: any) => l !== 'body').join(' -> ') : '';
          return locStr ? `${locStr}: ${d.msg}` : d.msg;
        }
        return d.detail || JSON.stringify(d);
      })
      .join('; ');
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.detail || detail.message || JSON.stringify(detail);
  }
  return defaultMsg;
}

export async function lookupPNR(pnr: string): Promise<PNRLookupResult> {
  const res = await fetch(`${BASE_URL}/auth/lookup-pnr`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify({ pnr: pnr.trim() }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: 'Failed to look up PNR' }));
    throw new Error(formatErrorMessage(errData.detail, `PNR '${pnr}' not found`));
  }

  return res.json();
}

export async function sendChatMessage(
  pnr: string,
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      pnr: pnr.trim(),
      message: message.trim(),
      conversation_id: conversationId,
    }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: 'Network response was not ok' }));
    throw new Error(formatErrorMessage(errData.detail, `Server error ${res.status}`));
  }

  return res.json();
}

export async function getConversationHistory(customer_id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/conversations/${customer_id}`, {
    headers: {
      'Authorization': `Bearer ${authToken}`,
    },
  });
  if (!res.ok) throw new Error('Failed to fetch conversation history');
  return res.json();
}

export async function addCustomer(customerData: Partial<Customer>): Promise<Customer> {
  const res = await fetch(`${BASE_URL}/admin/customers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify(customerData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create customer' }));
    throw new Error(formatErrorMessage(err.detail, 'Failed to create customer'));
  }
  return res.json();
}

export async function addBooking(bookingData: Partial<Booking>): Promise<Booking> {
  const res = await fetch(`${BASE_URL}/admin/bookings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`,
    },
    body: JSON.stringify(bookingData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create booking' }));
    throw new Error(formatErrorMessage(err.detail, 'Failed to create booking'));
  }
  return res.json();
}

export async function importCSV(customersFile?: File, bookingsFile?: File): Promise<any> {
  const formData = new FormData();
  if (customersFile) formData.append('customers_csv', customersFile);
  if (bookingsFile) formData.append('bookings_csv', bookingsFile);

  const res = await fetch(`${BASE_URL}/admin/import`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
    },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'CSV import failed' }));
    throw new Error(formatErrorMessage(err.detail, 'CSV import failed'));
  }
  return res.json();
}
