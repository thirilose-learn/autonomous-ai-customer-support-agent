import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ChatWindow } from './components/ChatWindow';
import { MessageInput } from './components/MessageInput';
import {
  checkBackendHealth,
  fetchDemoPersonas,
  selectDemoPersona,
  getCurrentCustomerProfile,
  getStoredCustomer,
  getApiBaseUrl,
  sendChatMessage,
  resetChat,
} from './services/api';

export default function App() {
  const [backendStatus, setBackendStatus] = useState('loading');
  const [backendError, setBackendError] = useState(null);
  const [backendData, setBackendData] = useState(null);

  // Persona & Session State
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState(getStoredCustomer());
  const [personaLoading, setPersonaLoading] = useState(false);
  const [personaError, setPersonaError] = useState(null);
  const [isAgentResponding, setIsAgentResponding] = useState(false);

  // In-memory per-persona conversation state for the active application session
  const [personaChats, setPersonaChats] = useState({});

  const getInitialGreeting = (persona) => {
    if (!persona) {
      return [
        {
          id: 'welcome-default',
          sender: 'assistant',
          isWelcome: true,
          text: "👋 Welcome! I am your AI Customer Support & Resolution Assistant.\n\nI can help you check order statuses, review return and refund policies, or connect you with a supervisor for complex inquiries.\n\nHow can I assist you today?",
        },
      ];
    }
    return [
      {
        id: `welcome-${persona.demo_customer_id}`,
        sender: 'assistant',
        isWelcome: true,
        text: `👋 Hello **${persona.display_name}**! Welcome to Customer Support.\n\nI have access to your account records for **${persona.customer_city || 'your location'}, ${persona.customer_state || 'BR'}** (${persona.total_orders} order${persona.total_orders === 1 ? '' : 's'} on file).\n\nHow can I help you today? You can ask me to track an order, explain our return/refund policies, or request assistance from a supervisor.`,
      },
    ];
  };

  const verifyHealth = async () => {
    setBackendStatus('loading');
    setBackendError(null);
    const result = await checkBackendHealth();
    if (result.connected) {
      setBackendStatus('connected');
      setBackendData(result.data);
    } else {
      setBackendStatus('disconnected');
      setBackendError(result.error);
    }
  };

  const loadPersonasAndSession = async () => {
    setPersonaLoading(true);
    setPersonaError(null);
    try {
      const list = await fetchDemoPersonas();
      setPersonas(list);

      // Verify active session or initialize with DEMO_00001
      const activeProfile = await getCurrentCustomerProfile();
      if (activeProfile) {
        setSelectedPersona(activeProfile);
        setPersonaChats((prev) => ({
          ...prev,
          [activeProfile.demo_customer_id]: prev[activeProfile.demo_customer_id] || getInitialGreeting(activeProfile),
        }));
      } else if (list.length > 0) {
        const defaultId = list[0].demo_customer_id;
        const session = await selectDemoPersona(defaultId);
        setSelectedPersona(session.customer);
        setPersonaChats((prev) => ({
          ...prev,
          [session.customer.demo_customer_id]: prev[session.customer.demo_customer_id] || getInitialGreeting(session.customer),
        }));
      }
    } catch (err) {
      setPersonaError(err.message || 'Failed to load demo personas.');
    } finally {
      setPersonaLoading(false);
    }
  };

  useEffect(() => {
    verifyHealth();
    loadPersonasAndSession();
  }, []);

  const handleSelectPersona = async (demoCustomerId) => {
    if (!demoCustomerId) return;
    setPersonaLoading(true);
    setPersonaError(null);
    try {
      const session = await selectDemoPersona(demoCustomerId);
      setSelectedPersona(session.customer);

      // Ensure newly selected persona has an initialized conversation if not yet started
      setPersonaChats((prev) => {
        if (!prev[demoCustomerId]) {
          return {
            ...prev,
            [demoCustomerId]: getInitialGreeting(session.customer),
          };
        }
        return prev;
      });
    } catch (err) {
      setPersonaError(err.message || 'Failed to switch persona.');
    } finally {
      setPersonaLoading(false);
    }
  };

  const activePersonaId = selectedPersona?.demo_customer_id;
  const currentMessages = activePersonaId
    ? (personaChats[activePersonaId] || getInitialGreeting(selectedPersona))
    : getInitialGreeting(null);

  const handleSendMessage = async (text) => {
    if (!text || !text.trim() || isAgentResponding) return;
    const personaId = selectedPersona?.demo_customer_id;
    if (!personaId) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: text.trim(),
    };

    setPersonaChats((prev) => {
      const existing = prev[personaId] || getInitialGreeting(selectedPersona);
      return {
        ...prev,
        [personaId]: [...existing, userMsg],
      };
    });
    setIsAgentResponding(true);

    try {
      const agentResult = await sendChatMessage(text.trim());
      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: agentResult.response,
        intent: agentResult.intent,
        tools_executed: agentResult.tools_executed,
        tool_details: agentResult.tool_details,
        latency_ms: agentResult.latency_ms,
      };
      setPersonaChats((prev) => {
        const existing = prev[personaId] || [];
        return {
          ...prev,
          [personaId]: [...existing, assistantMsg],
        };
      });
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: `⚠️ **Agent Error**: ${err.message || 'Unable to process inquiry. Please ensure backend is running.'}`,
        isError: true,
      };
      setPersonaChats((prev) => {
        const existing = prev[personaId] || [];
        return {
          ...prev,
          [personaId]: [...existing, errorMsg],
        };
      });
    } finally {
      setIsAgentResponding(false);
    }
  };

  const handleSelectPrompt = (promptText) => {
    handleSendMessage(promptText);
  };

  return (
    <div className="app-container">
      <Header
        backendStatus={backendStatus}
        backendError={backendError}
        onRetryBackend={verifyHealth}
        personas={personas}
        selectedPersona={selectedPersona}
        personaLoading={personaLoading || isAgentResponding}
        personaError={personaError}
        onSelectPersona={handleSelectPersona}
      />

      <ChatWindow
        messages={currentMessages}
        isAgentResponding={isAgentResponding}
        onSelectPrompt={handleSelectPrompt}
      />
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isAgentResponding}
      />
    </div>
  );
}
