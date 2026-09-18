import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { CustomerBanner } from './components/CustomerBanner';
import { ChatWindow } from './components/ChatWindow';
import { ActionLogPanel } from './components/ActionLogPanel';
import { AdminModal } from './components/AdminModal';
import { LoginScreen } from './components/LoginScreen';
import type { ChatMessage, ActionItem, EscalationItem, Customer, Booking } from './types';
import { sendChatMessage, loginWithToken, lookupPNR } from './api/client';
import type { PNRLookupResult } from './api/client';

export const App: React.FC = () => {
  const [activePnr, setActivePnr] = useState<string>('');
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAdminOpen, setIsAdminOpen] = useState<boolean>(false);

  const [isDetailsOpen, setIsDetailsOpen] = useState<boolean>(false);
  const [hasAutoOpenedDetails, setHasAutoOpenedDetails] = useState<boolean>(false);

  // Initialize auth token on mount
  useEffect(() => {
    loginWithToken('dev_secret_token_123');
  }, []);

  // Quick prompts based on active PNR
  const getQuickPrompts = () => {
    if (activePnr === 'SK4821X') {
      return [
        'Request refund for cancelled flight',
        'Request free rebooking on next flight',
        'Demand business class upgrade + cash',
        'Threaten legal action'
      ];
    } else if (activePnr === 'TR1190B') {
      return [
        'What benefits am I entitled to for 4h delay?',
        'Request hotel room for 4h delay',
        'Issue meal voucher & lounge access'
      ];
    } else if (activePnr === 'WL7742') {
      return [
        'Request meal, lounge, and hotel for 6h delay',
        'Request full night hotel stay',
        'Ask for ₹2000 fare waiver'
      ];
    }
    return [
      'What is my flight status?',
      'Request compensation benefits'
    ];
  };

  const handleLoginSuccess = (data: PNRLookupResult) => {
    setActivePnr(data.pnr);
    setIsLoggedIn(true);
    const custData = {
      id: String(data.customer_id),
      name: data.name,
      loyalty_tier: data.loyalty_tier,
      contact: data.contact,
      flights_last_12mo: data.flights_last_12mo,
      prior_complaints: data.prior_complaints,
    };
    setCustomer(custData);
    setBooking(data.booking);
    setActions([]);
    setEscalations([]);
    setConversationId(undefined);
    setIsDetailsOpen(false);
    setHasAutoOpenedDetails(false);

    // Proactive Agent Greeting
    const firstName = data.name ? data.name.split(' ')[0] : 'there';
    let welcomeText = `Hi ${firstName}, welcome! How can I assist you with your booking today?`;
    if (data.booking?.status === 'CANCELLED') {
      welcomeText = `Hi ${firstName}, I can see flight ${data.booking.flight_number} to ${data.booking.route_dest} was cancelled — I'm so sorry about this disruption. How can I help you today?`;
    } else if (data.booking?.status === 'DELAYED') {
      const delayInfo = data.booking.delay_hours ? `${data.booking.delay_hours} hours` : 'delayed';
      welcomeText = `Hi ${firstName}, I can see flight ${data.booking.flight_number} to ${data.booking.route_dest} is delayed ${delayInfo} — sorry about the wait! How can I help?`;
    }

    const initialMsg: ChatMessage = {
      id: `agent-welcome-${Date.now()}`,
      sender: 'agent',
      text: welcomeText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages([initialMsg]);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setActivePnr('');
    setCustomer(null);
    setBooking(null);
    setMessages([]);
    setActions([]);
    setEscalations([]);
    setConversationId(undefined);
    setIsDetailsOpen(false);
    setHasAutoOpenedDetails(false);
  };

  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await sendChatMessage(activePnr, text, conversationId);
      
      setConversationId(res.conversation_id);
      if (res.customer_info) setCustomer(res.customer_info);
      if (res.booking_info) setBooking(res.booking_info);

      if (res.actions_taken && res.actions_taken.length > 0) {
        const datedActions = res.actions_taken.map(a => ({
          ...a,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }));
        setActions((prev) => [...prev, ...datedActions]);
      }

      if (res.escalations && res.escalations.length > 0) {
        const datedEscalations = res.escalations.map(e => ({
          ...e,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }));
        setEscalations((prev) => [...prev, ...datedEscalations]);

        // Auto-open Details panel ONCE per session on first escalation
        if (!hasAutoOpenedDetails) {
          setIsDetailsOpen(true);
          setHasAutoOpenedDetails(true);
        }
      }

      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        intents: res.intents,
        policy_cites: res.policy_cites,
        actions: res.actions_taken,
        escalations: res.escalations,
      };

      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'agent',
        text: `⚠️ Error communicating with backend: ${err.message || 'Make sure FastAPI backend is running on http://localhost:8000'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdminSuccess = async (newPnr: string) => {
    setIsAdminOpen(false);
    try {
      const data = await lookupPNR(newPnr);
      handleLoginSuccess(data);
    } catch (err) {
      setActivePnr(newPnr);
      setIsLoggedIn(true);
    }
  };

  if (!isLoggedIn) {
    return (
      <>
        <LoginScreen
          onSuccess={handleLoginSuccess}
          onOpenAdmin={() => setIsAdminOpen(true)}
        />
        <AdminModal
          isOpen={isAdminOpen}
          onClose={() => setIsAdminOpen(false)}
          onSuccess={handleAdminSuccess}
        />
      </>
    );
  }

  return (
    <div className="app-container">
      <Header
        customer={customer}
        activePnr={activePnr}
        onLogout={handleLogout}
        onOpenAdmin={() => setIsAdminOpen(true)}
      />

      <div className="main-content" style={{ gridTemplateColumns: '1fr', padding: '16px max(16px, calc((100vw - 1100px) / 2))' }}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
          <CustomerBanner
            customer={customer}
            booking={booking}
            fallbackPnr={activePnr}
          />
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            quickPrompts={getQuickPrompts()}
            onToggleDetails={() => setIsDetailsOpen((prev) => !prev)}
            isDetailsOpen={isDetailsOpen}
            actionsCount={actions.length}
            escalationsCount={escalations.length}
          />
        </div>

        <ActionLogPanel
          isOpen={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          actions={actions}
          escalations={escalations}
          customer={customer}
          booking={booking}
        />
      </div>

      <AdminModal
        isOpen={isAdminOpen}
        onClose={() => setIsAdminOpen(false)}
        onSuccess={handleAdminSuccess}
      />
    </div>
  );
};

export default App;
