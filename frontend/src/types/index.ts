export interface Customer {
  id: string;
  name: string;
  loyalty_tier: 'Silver' | 'Gold' | 'Platinum' | 'Standard' | 'Base';
  contact?: string;
  flights_last_12mo: number;
  prior_complaints?: string[];
}

export interface Booking {
  id: string;
  pnr: string;
  customer_id: string;
  flight_number: string;
  route_origin: string;
  route_dest: string;
  flight_date: string;
  scheduled_departure: string;
  actual_departure?: string;
  status: 'CANCELLED' | 'DELAYED' | 'ON_TIME';
  delay_hours: number;
}

export interface ActionItem {
  type: string;
  details: Record<string, any>;
  escalated: boolean;
  timestamp: string;
}

export interface EscalationItem {
  reason: string;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  intents?: string[];
  policy_cites?: string[];
  actions?: ActionItem[];
  escalations?: EscalationItem[];
  booking_info?: {
    pnr: string;
    customer_name: string;
    flight_number: string;
    status: string;
    delay_hours: number;
  };
}

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  pnr: string;
  customer_name?: string;
  intents: string[];
  policy_cites: string[];
  actions_taken: ActionItem[];
  escalations: EscalationItem[];
  customer_info?: Customer;
  booking_info?: Booking;
}

export interface PresetCustomer {
  label: string;
  name: string;
  pnr: string;
  tier: 'Silver' | 'Gold' | 'Platinum';
  status: string;
  route: string;
  samplePrompt: string;
  description: string;
}
