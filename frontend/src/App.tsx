import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { CustomerBanner } from './components/CustomerBanner';
import { ChatWindow } from './components/ChatWindow';
import { ActionLogPanel } from './components/ActionLogPanel';
import { AdminModal } from './components/AdminModal';
import type { PresetCustomer, ChatMessage, ActionItem, EscalationItem, Customer, Booking } from './types';
import { sendChatMessage, loginWithToken } from './api/client';

const PRESET_CUSTOMERS: PresetCustomer[] = [
  {
    label: 'Priya Nair',
    name: 'Priya Nair',
    pnr: 'SK4821X',
    tier: 'Gold',
    status: 'CANCELLED',
    route: 'DEL → BOM',
    samplePrompt: 'My flight was cancelled! I want a full refund and a free business class upgrade.',
    description: 'Gold tier customer with cancelled flight SK4821X.',
  },
  {
    label: 'Arvind Kulkarni',
    name: 'Arvind Kulkarni',
    pnr: 'TR1190B',
    tier: 'Silver',
    status: 'DELAYED (4h)',
    route: 'BOM → BLR',
    samplePrompt: 'My flight is delayed 4 hours. Give me a meal voucher, lounge access, and a hotel room.',
    description: 'Silver tier customer with 4-hour flight delay.',
  },
  {
    label: 'Meher Kaur',
    name: 'Meher Kaur',
    pnr: 'WL7742',
    tier: 'Platinum',
    status: 'DELAYED (6h)',
    route: 'DEL → MAA',
    samplePrompt: 'My flight is delayed 6 hours. I demand meal vouchers, lounge, hotel room, and a ₹2000 fare waiver!',
    description: 'Platinum tier customer with 6-hour delay and multi-ask.',
  },
];

export const App: React.FC = () => {
  const [activePreset, setActivePreset] = useState<PresetCustomer>(PRESET_CUSTOMERS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAdminOpen, setIsAdminOpen] = useState<boolean>(false);

  // Initialize auth token on mount
  useEffect(() => {
    loginWithToken('dev_secret_token_123');
  }, []);

  // Quick prompts based on active preset
  const getQuickPrompts = () => {
    if (activePreset.pnr === 'SK4821X') {
      return [
        'Request refund for cancelled flight',
        'Request free rebooking on next flight',
        'Demand business class upgrade + cash',
        'Threaten legal action'
      ];
    } else if (activePreset.pnr === 'TR1190B') {
      return [
        'What benefits am I entitled to for 4h delay?',
        'Request hotel room for 4h delay',
        'Issue meal voucher & lounge access'
      ];
    } else if (activePreset.pnr === 'WL7742') {
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

  const handleSelectPreset = (preset: PresetCustomer) => {
    setActivePreset(preset);
    setMessages([]);
    setActions([]);
    setEscalations([]);
    setCustomer(null);
    setBooking(null);
    setConversationId(undefined);
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
      const res = await sendChatMessage(activePreset.pnr, text, conversationId);
      
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

  const handleAdminSuccess = (newPnr: string) => {
    setIsAdminOpen(false);
    const customPreset: PresetCustomer = {
      label: `PNR: ${newPnr}`,
      name: `Passenger ${newPnr}`,
      pnr: newPnr,
      tier: 'Gold',
      status: 'ADDED',
      route: 'NEW ROUTE',
      samplePrompt: 'Please resolve my flight disruption issue.',
      description: `Newly ingested passenger via Admin Portal (${newPnr}).`
    };
    setActivePreset(customPreset);
    setMessages([]);
    setActions([]);
    setEscalations([]);
    setCustomer(null);
    setBooking(null);
  };

  return (
    <div className="app-container">
      <Header
        presets={PRESET_CUSTOMERS}
        activePnr={activePreset.pnr}
        onSelectPreset={handleSelectPreset}
        onOpenAdmin={() => setIsAdminOpen(true)}
      />

      <div className="main-content">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
          <CustomerBanner
            customer={customer}
            booking={booking}
            fallbackPnr={activePreset.pnr}
          />
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            quickPrompts={getQuickPrompts()}
          />
        </div>

        <ActionLogPanel
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
