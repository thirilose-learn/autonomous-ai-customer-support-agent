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

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'assistant',
      isWelcome: true,
      text: "👋 Welcome to the Autonomous AI Customer Support & Resolution Agent.\n\nLevel 5 Agent Architecture is live! Select a customer persona above to ground conversations in authentic customer orders, execute policy RAG knowledge searches, or request human escalation.",
    },
  ]);

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
      } else if (list.length > 0) {
        const defaultId = list[0].demo_customer_id;
        const session = await selectDemoPersona(defaultId);
        setSelectedPersona(session.customer);
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

      const notifyMsg = {
        id: Date.now(),
        sender: 'assistant',
        text: `Switched customer persona to **${session.customer.display_name}** (${session.customer.demo_customer_id}).\n\n• **Scenario**: \`${session.customer.primary_scenario}\`\n• **Lifetime Orders**: ${session.customer.total_orders}\n• **Location**: ${session.customer.customer_city || 'N/A'}, ${session.customer.customer_state || 'N/A'}\n• **Sample Order ID**: \`${session.customer.sample_order_id || 'N/A'}\`\n\nAll subsequent customer-scoped inquiries and tool executions will be strictly bound to this identity.`,
      };
      setMessages((prev) => [...prev, notifyMsg]);
    } catch (err) {
      setPersonaError(err.message || 'Failed to switch persona.');
    } finally {
      setPersonaLoading(false);
    }
  };

  const handleSendMessage = async (text) => {
    if (!text || !text.trim() || isAgentResponding) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: text.trim(),
    };

    setMessages((prev) => [...prev, userMsg]);
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
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: `⚠️ **Agent Error**: ${err.message || 'Unable to process inquiry. Please ensure backend is running.'}`,
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
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
        personaLoading={personaLoading}
        personaError={personaError}
        onSelectPersona={handleSelectPersona}
      />

      {selectedPersona && (
        <div className="active-customer-banner">
          <div>
            👤 Active Persona: <strong>{selectedPersona.display_name}</strong> ({selectedPersona.demo_customer_id}) &bull; Scenario: <em>{selectedPersona.primary_scenario}</em>
          </div>
          <div>
            📍 {selectedPersona.customer_city || 'City'}, {selectedPersona.customer_state || 'ST'} &bull; Orders: <strong>{selectedPersona.total_orders}</strong>
          </div>
        </div>
      )}

      <ChatWindow
        messages={messages}
        onSelectPrompt={handleSelectPrompt}
      />
      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isAgentResponding}
      />
    </div>
  );
}
