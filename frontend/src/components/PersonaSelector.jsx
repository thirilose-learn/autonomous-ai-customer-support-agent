import React from 'react';

export function PersonaSelector({
  personas,
  selectedPersona,
  loading,
  error,
  onSelectPersona,
}) {
  return (
    <div className="persona-selector-container">
      <div className="persona-chip" title="Active Customer Persona Context">
        <div className="persona-icon">
          {selectedPersona?.demo_customer_id?.replace('DEMO_', '#') || 'ID'}
        </div>
        <select
          className="persona-dropdown"
          value={selectedPersona?.demo_customer_id || ''}
          onChange={(e) => onSelectPersona(e.target.value)}
          disabled={loading || personas.length === 0}
          aria-label="Select Demo Customer Persona"
        >
          {personas.length === 0 ? (
            <option value="">{loading ? 'Loading personas...' : 'No personas found'}</option>
          ) : (
            personas.map((p) => (
              <option key={p.demo_customer_id} value={p.demo_customer_id}>
                {p.demo_customer_id}: {p.display_name} — {p.primary_scenario} ({p.customer_city || 'City'}, {p.customer_state || 'ST'})
              </option>
            ))
          )}
        </select>
      </div>
      {error && <span className="persona-error-tooltip" title={error}>!</span>}
    </div>
  );
}
